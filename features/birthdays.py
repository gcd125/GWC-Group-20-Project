"""Birthday cards, manual birthday tests, and daily birthday scheduling."""
import datetime as dt
import logging
import os
import discord
from discord.ext import tasks

LOG = logging.getLogger(__name__)

def birthday_matches(value, today):
    """Accept ISO YYYY-MM-DD or MM-DD; February 29 is leap-years only."""
    if not value:
        return False
    value = str(value).strip()
    try:
        birthday = dt.date.fromisoformat('2000-' + value if len(value) == 5 else value)
    except ValueError:
        return False
    return (birthday.month, birthday.day) == (today.month, today.day)


def birthday_members(db, today):
    return [row for row in db.execute("SELECT * FROM Members WHERE member_status = 'active'")
            if birthday_matches(row['member_dob'], today)]


def greeting(member):
    name = discord.utils.escape_mentions(discord.utils.escape_markdown(member['first_name']))[:100]
    return (f'🎉 Happy birthday, {name}! 💖 Your Girls Who Code family wishes you '
            'a day full of joy, cake, and a little coding magic! 🎂✨')


def birthday_embed(member, *, thumbnail_url=None):
    name = discord.utils.escape_mentions(discord.utils.escape_markdown(member['first_name']))[:100]
    embed = discord.Embed(
        title=f'🎂 Happy Birthday, {name}! ✨',
        description=(
            f'Hey **{name}**! 💙\n\n'
            'Your **Girls Who Code @ UCF** family is celebrating you today!\n\n'
            '🌸 Wishing you a day full of joy and cake\n'
            '💻 A year of big ideas and coding adventures\n'
            '✨ And plenty of moments that make you smile!\n\n'
            '**We’re so glad you’re part of our community. Have an amazing birthday!** 🎉'
        ),
        colour=0x82A7DB,
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    footer = 'Girls Who Code @ UCF 🤍 Code • Connect • Create'
    embed.set_footer(text=footer)
    return embed


def claim(db, member_id, year):
    with db:
        result = db.execute('INSERT OR IGNORE INTO Birthday_Greetings VALUES (?, ?, ?, NULL)',
                            (member_id, year, 'pending'))
    return result.rowcount == 1


async def send_birthdays(db, channel, today, *, thumbnail_url=None, member_id=None):
    for member in birthday_members(db, today):
        if member_id is not None and member["member_id"] != member_id:
            continue
        if not claim(db, member['member_id'], today.year):
            continue
        try:
            message = await channel.send(embed=birthday_embed(member, thumbnail_url=thumbnail_url), allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            # Keep pending: a timeout may mean Discord accepted the message.
            # An operator must reconcile before retrying, avoiding duplicate wishes.
            LOG.exception('Birthday delivery unresolved for member %s; inspect pending record', member['member_id'])
            continue
        with db:
            db.execute("UPDATE Birthday_Greetings SET status = 'sent', message_id = ? WHERE member_id = ? AND birthday_year = ?",
                       (str(message.id), member['member_id'], today.year))


def initialize_birthdays(db):
    db.execute('''CREATE TABLE IF NOT EXISTS Birthday_Greetings (
        member_id INTEGER NOT NULL, birthday_year INTEGER NOT NULL,
        status TEXT NOT NULL, message_id TEXT,
        PRIMARY KEY (member_id, birthday_year)
    )''')
    db.commit()

class BirthdayFeature:
    def __init__(self, bot):
        self.bot = bot

    def start(self):
        initialize_birthdays(self.bot.db)
        if not self.bot.test_mode:
            self.check_birthdays.start()

    def stop(self):
        self.check_birthdays.cancel()

    async def handle_registration(self, member_id, guild):
        """Celebrate a newly saved birthday immediately, including in test mode."""
        today = dt.datetime.now(self.bot.timezone).date()
        member = self.bot.db.execute('SELECT * FROM Members WHERE member_id=?', (member_id,)).fetchone()
        if not member or member['member_status'] != 'active' or not birthday_matches(member['member_dob'], today):
            return
        configured = os.environ.get('GENERAL_CHANNEL_ID', '').strip()
        if configured:
            channel = guild.get_channel(int(configured)) if configured.isdigit() else None
        else:
            channels = [c for c in guild.text_channels if c.name == 'general']
            channel = channels[0] if len(channels) == 1 else None
        if channel is None:
            LOG.error('Birthday registration delivery: set GENERAL_CHANNEL_ID or provide a unique #general channel')
            return
        initialize_birthdays(self.bot.db)
        await send_birthdays(self.bot.db, channel, today,
                             thumbnail_url=self.birthday_thumbnail(), member_id=member_id)

    async def handle_message(self, message):
        if message.author.bot or message.guild is None:
            return
        parts = message.content.split()
        if not parts or parts[0].lower() != '!testbirthday':
            return
        async def reply(text):
            await message.channel.send(text, allowed_mentions=discord.AllowedMentions.none())
        if not message.author.guild_permissions.manage_guild:
            await reply('You need Manage Server permission to run birthday tests.')
            return
        if not self.bot.test_mode:
            await reply('Restart the bot with --test-mode to use !testbirthday.')
            return
        try:
            if len(parts) > 2:
                raise ValueError
            day = dt.date.fromisoformat(parts[1]) if len(parts) == 2 else dt.datetime.now(self.bot.timezone).date()
        except ValueError:
            await reply('Usage: !testbirthday [YYYY-MM-DD], for example !testbirthday 2026-11-03')
            return
        members = birthday_members(self.bot.db, day)
        if not members:
            await reply(f'No active member birthdays on {day}.')
            return
        for member in members:
            await message.channel.send(
                embed=birthday_embed(member, thumbnail_url=self.birthday_thumbnail()),
                allowed_mentions=discord.AllowedMentions.none(),
            )

    def birthday_thumbnail(self):
        return os.environ.get('BIRTHDAY_IMAGE_URL') or (str(self.bot.user.display_avatar.url) if self.bot.user else None)

    @tasks.loop(minutes=1)
    async def check_birthdays(self):
        now = dt.datetime.now(self.bot.timezone)
        if now.time() < self.bot.send_time:
            return
        try:
            channel = self.bot.get_channel(self.bot.channel_id) or await self.bot.fetch_channel(self.bot.channel_id)
            if not isinstance(channel, discord.TextChannel):
                raise ValueError('GENERAL_CHANNEL_ID must identify a server text channel')
            await send_birthdays(self.bot.db, channel, now.date(), thumbnail_url=self.birthday_thumbnail())
        except Exception:
            LOG.exception('Birthday check failed; will check again next minute')

    @check_birthdays.before_loop
    async def before_birthdays(self):
        await self.bot.wait_until_ready()
