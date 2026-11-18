"""Persistent opt-in giveaways: creation modal, entry button, and timed draw."""
import logging
import os
import re
import secrets
import sqlite3
import time
import discord
from discord.ext import tasks

LOG = logging.getLogger(__name__)
FOOTER = 'Girls Who Code @ UCF 🤍 Code • Connect • Create'


def parse_duration(value):
    match = re.fullmatch(r'\s*(\d{1,8})\s*([smhd])\s*', value.lower())
    if not match:
        raise ValueError('Use a duration like 30s, 10m, 2h, or 7d.')
    seconds = int(match[1]) * {'s':1,'m':60,'h':3600,'d':86400}[match[2]]
    if not 10 <= seconds <= 30 * 86400:
        raise ValueError('Duration must be between 10 seconds and 30 days.')
    return seconds


class GiveawayStore:
    def __init__(self, db):
        self.db = db

    def initialize(self):
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS Giveaways (
                id INTEGER PRIMARY KEY, guild_id TEXT NOT NULL, channel_id TEXT NOT NULL,
                message_id TEXT UNIQUE, host_id TEXT NOT NULL, name TEXT NOT NULL,
                ends_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
                winner_id TEXT, eligible_count INTEGER, published INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS Giveaway_Entries (
                giveaway_id INTEGER NOT NULL, discord_id TEXT NOT NULL, member_id INTEGER NOT NULL,
                PRIMARY KEY(giveaway_id, discord_id), UNIQUE(giveaway_id, member_id)
            );
        ''')

        # Additive migration: existing giveaways and entries are preserved.
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(Giveaways)')}
        with self.db:
            for name, kind in [('prize', 'TEXT'), ('created_at', 'INTEGER'),
                               ('finished_at', 'INTEGER'), ('winner_member_id', 'INTEGER'),
                               ('announcement_message_id', 'TEXT'), ('announced', 'INTEGER NOT NULL DEFAULT 0')]:
                if name not in columns:
                    self.db.execute(f'ALTER TABLE Giveaways ADD COLUMN {name} {kind}')

        if 'announced' not in columns:
            # Do not announce results that were already published before this upgrade.
            with self.db:
                self.db.execute("UPDATE Giveaways SET announced=1 WHERE status='finished' AND published=1")

    def get(self, giveaway_id):
        return self.db.execute('SELECT * FROM Giveaways WHERE id=?', (giveaway_id,)).fetchone()

    def create(self, guild_id, channel_id, host_id, name, duration, now=None, prize=None):
        name = ' '.join(name.split())
        if not 1 <= len(name) <= 100:
            raise ValueError('Giveaway name must contain 1–100 characters.')
        if not 10 <= duration <= 30*86400:
            raise ValueError('Duration must be between 10 seconds and 30 days.')
        prize = ' '.join((name if prize is None else prize).split())
        if not 1 <= len(prize) <= 200:
            raise ValueError('Prize must contain 1–200 characters.')
        created_at = int(time.time() if now is None else now)
        with self.db:
            cursor = self.db.execute('INSERT INTO Giveaways(guild_id,channel_id,host_id,name,ends_at,prize,created_at) VALUES(?,?,?,?,?,?,?)',
                (str(guild_id),str(channel_id),str(host_id),name,created_at+duration,prize,created_at))
        return cursor.lastrowid

    def activate(self, giveaway_id, message_id):
        with self.db:
            self.db.execute("UPDATE Giveaways SET message_id=?,status='active' WHERE id=? AND status='draft'", (str(message_id),giveaway_id))

    def enter(self, message_id, guild_id, discord_id, now=None):
        now = int(time.time() if now is None else now)
        with self.db:
            # Lock before eligibility/deadline checks so entry and draw cannot race.
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT * FROM Giveaways WHERE message_id=? AND guild_id=?', (str(message_id),str(guild_id))).fetchone()
            if not row or row['status'] != 'active' or now >= row['ends_at']:
                raise ValueError('This giveaway is closed or no longer available.')
            member = self.db.execute('''SELECT m.member_id FROM Members m JOIN Member_Discord_Links l ON l.member_id=m.member_id
                WHERE l.guild_id=? AND l.discord_id=? AND m.member_status='active' ''', (str(guild_id),str(discord_id))).fetchone()
            if not member:
                raise ValueError('Complete Start Registration from /registration, then click Enter Giveaway again. If you already registered, ask an organizer to check your account link and active membership status.')
            result = self.db.execute('INSERT OR IGNORE INTO Giveaway_Entries VALUES(?,?,?)', (row['id'],str(discord_id),member[0]))
            return result.rowcount == 1

    def finish(self, giveaway_id, now=None, chooser=secrets.choice):
        now = int(time.time() if now is None else now)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.get(giveaway_id)
            if row is None or row['status'] != 'active' or row['ends_at'] > now:
                return row
            eligible = self.db.execute('''SELECT e.discord_id, e.member_id FROM Giveaway_Entries e
                JOIN Members m ON m.member_id=e.member_id
                JOIN Member_Discord_Links l ON l.member_id=e.member_id AND l.discord_id=e.discord_id AND l.guild_id=?
                WHERE e.giveaway_id=? AND m.member_status='active' ORDER BY e.discord_id''', (row['guild_id'],giveaway_id)).fetchall()
            winner = chooser(eligible) if eligible else None
            self.db.execute("UPDATE Giveaways SET status='finished',winner_id=?,eligible_count=?,finished_at=?,winner_member_id=? WHERE id=?",
                (winner[0] if winner else None,len(eligible),now,winner[1] if winner else None,giveaway_id))
        return self.get(giveaway_id)

    def pending(self, now=None):
        return self.db.execute("SELECT id FROM Giveaways WHERE (status='active' AND ends_at<=?) OR (status='finished' AND (published=0 OR announced=0))", (int(time.time() if now is None else now),)).fetchall()


def giveaway_embed(row, thumbnail=None):
    name = discord.utils.escape_mentions(discord.utils.escape_markdown(row['name']))
    if row['status'] == 'finished':
        result = f"🎉 Congratulations, <@{row['winner_id']}>!" if row['winner_id'] else 'No eligible members entered this giveaway.'
        description = f"**Giveaway ended**\n\n{result}\n\nEligible entries: **{row['eligible_count']}**"
    else:
        description = (f"Click **Enter Giveaway** below for your chance to win! 🎉\n\n"
            f"⏰ Ends <t:{row['ends_at']}:R> · <t:{row['ends_at']}:f>\n\n"
            'One entry per registered member. A winner will be randomly selected from eligible entrants when time is up. 💙')
    embed = discord.Embed(title=f'🎁 {name}', description=description, colour=0x82A7DB)
    if row['prize']:
        embed.add_field(name='Prize', value=discord.utils.escape_mentions(discord.utils.escape_markdown(row['prize'])), inline=False)
    embed.set_footer(text=FOOTER)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed


class GiveawayModal(discord.ui.Modal, title='New Giveaway'):
    name_input = discord.ui.TextInput(label='Giveaway name', placeholder='Fall Shirt Giveaway', max_length=100)
    prize_input = discord.ui.TextInput(label='Prize', placeholder='One GWC fall shirt', max_length=200)
    duration_input = discord.ui.TextInput(label='How long should it last?', placeholder='30s, 10m, 2h, or 7d', max_length=20)

    def __init__(self, feature):
        super().__init__(timeout=300)
        self.feature = feature

    async def on_submit(self, interaction):
        await self.feature.create_from_modal(interaction, str(self.name_input), str(self.duration_input), str(self.prize_input))


class NewGiveawayView(discord.ui.View):
    def __init__(self, feature):
        super().__init__(timeout=None)
        self.feature = feature

    @discord.ui.button(label='New Giveaway', emoji='🎁', style=discord.ButtonStyle.primary, custom_id='gwc:giveaway:new:v1')
    async def new(self, interaction, button):
        if not self.feature.can_host(interaction.user) or interaction.guild is None:
            await interaction.response.send_message('You do not have permission to start a giveaway here.', ephemeral=True)
            return
        await interaction.response.send_modal(GiveawayModal(self.feature))


class EnterGiveawayView(discord.ui.View):
    def __init__(self, feature):
        super().__init__(timeout=None)
        self.feature = feature

    @discord.ui.button(label='Enter Giveaway', emoji='🎉', style=discord.ButtonStyle.success, custom_id='gwc:giveaway:enter:v1')
    async def enter(self, interaction, button):
        if interaction.guild is None or interaction.user.bot:
            await interaction.response.send_message('Enter from your club server using a member account.', ephemeral=True)
            return
        try:
            added = self.feature.store.enter(interaction.message.id, interaction.guild.id, interaction.user.id)
            text = 'You’re entered! Good luck! 💙' if added else 'You’re already entered—one entry per member. 💙'
        except ValueError as error:
            text = str(error)
        await interaction.response.send_message(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


class GiveawayFeature:
    def __init__(self, bot):
        self.bot = bot
        self.store = GiveawayStore(bot.db)
        # Open hosting for now; set a role ID later. Managers always qualify.
        role = os.environ.get('GIVEAWAY_HOST_ROLE_ID', '').strip()
        self.host_role_id = int(role) if role else None
        self.views = []

    def can_host(self, user):
        return not user.bot and (self.host_role_id is None or user.guild_permissions.manage_guild or any(role.id == self.host_role_id for role in user.roles))

    def thumbnail(self):
        return str(self.bot.user.display_avatar.url) if self.bot.user else None

    def start(self):
        self.store.initialize()
        self.views = [NewGiveawayView(self), EnterGiveawayView(self)]
        for view in self.views:
            self.bot.add_view(view)
        self.check_deadlines.start()

    def stop(self):
        self.check_deadlines.cancel()
        for view in self.views:
            view.stop()

    def creation_embed(self):
        embed = discord.Embed(title='🎁 Girls Who Code Giveaways', description='Ready to celebrate? Click **New Giveaway** to choose a name, prize, and how long entries stay open.', colour=0x82A7DB)
        embed.set_footer(text=FOOTER)
        if self.thumbnail():
            embed.set_thumbnail(url=self.thumbnail())
        return embed

    async def handle_interaction(self, interaction):
        if interaction.guild is None or not self.can_host(interaction.user):
            await interaction.response.send_message('You do not have permission to start a giveaway here.', ephemeral=True)
            return
        embed = self.creation_embed()
        await interaction.response.send_message(embed=embed, view=NewGiveawayView(self), ephemeral=True,
                                                allowed_mentions=discord.AllowedMentions.none())

    async def handle_message(self, message):
        if not self.can_host(message.author):
            await message.channel.send('You do not have permission to start a giveaway.', allowed_mentions=discord.AllowedMentions.none())
            return
        embed = self.creation_embed()
        await message.channel.send(embed=embed, view=NewGiveawayView(self), allowed_mentions=discord.AllowedMentions.none())

    async def create_from_modal(self, interaction, name, duration, prize=None):
        if interaction.guild is None or not self.can_host(interaction.user):
            await interaction.response.send_message('You do not have permission to start a giveaway here.', ephemeral=True)
            return
        try:
            seconds = parse_duration(duration)
            clean_name = ' '.join(name.split())
            clean_prize = ' '.join((name if prize is None else prize).split())
            if not 1 <= len(clean_prize) <= 200:
                raise ValueError('Prize must contain 1–200 characters.')
            if not 1 <= len(clean_name) <= 100:
                raise ValueError('Giveaway name must contain 1–100 characters.')
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        giveaway_id = self.store.create(interaction.guild.id, interaction.channel.id, interaction.user.id, clean_name, seconds, prize=clean_prize)
        try:
            message = await interaction.channel.send(embed=giveaway_embed(self.store.get(giveaway_id),self.thumbnail()), view=EnterGiveawayView(self), allowed_mentions=discord.AllowedMentions.none())
            self.store.activate(giveaway_id, message.id)
        except Exception:
            LOG.exception('Giveaway %s could not be activated; inspect draft and channel before retrying', giveaway_id)
            await interaction.followup.send('The giveaway could not be activated. Ask an organizer to check the bot log before trying again.', ephemeral=True)
            return
        await interaction.followup.send(f'Giveaway started! {message.jump_url}', ephemeral=True)

    async def settle_due(self):
        for item in self.store.pending():
            try:
                row = self.store.finish(item['id'])
                channel = self.bot.get_channel(int(row['channel_id'])) or await self.bot.fetch_channel(int(row['channel_id']))
                if not row['published']:
                    message = await channel.fetch_message(int(row['message_id']))
                    await message.edit(embed=giveaway_embed(row,self.thumbnail()), view=None, allowed_mentions=discord.AllowedMentions.none())
                    with self.bot.db:
                        self.bot.db.execute('UPDATE Giveaways SET published=1 WHERE id=?', (row['id'],))
                if not row['announced']:
                    await self.announce_winner(channel, row)
            except Exception:
                LOG.exception('Could not publish giveaway %s result; will retry without redrawing', item['id'])

    async def announce_winner(self, channel, row):
        announcement_id = None
        if row['winner_id']:
            # Recover a send that succeeded before the database commit or HTTP response.
            marker = f"{FOOTER} | Giveaway #{row['id']}"
            async for message in channel.history(after=discord.Object(id=int(row['message_id'])), limit=None):
                if message.author.id == self.bot.user.id and any(embed.footer.text == marker for embed in message.embeds):
                    announcement_id = str(message.id)
                    break
            if announcement_id is None:
                prize = discord.utils.escape_mentions(discord.utils.escape_markdown(row['prize'] or row['name']))
                name = discord.utils.escape_mentions(discord.utils.escape_markdown(row['name']))
                embed = discord.Embed(title='🎉 Congratulations!',
                    description=f"<@{row['winner_id']}> won **{prize}**!\n\nThank you to everyone who entered **{name}**! 💙",
                    colour=0x82A7DB)
                embed.set_footer(text=marker)
                if self.thumbnail():
                    embed.set_thumbnail(url=self.thumbnail())
                message = await channel.send(content=f"🎉 Congratulations, <@{row['winner_id']}>!", embed=embed,
                    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False,
                        users=[discord.Object(id=int(row['winner_id']))], replied_user=False))
                announcement_id = str(message.id)
        with self.bot.db:
            self.bot.db.execute('UPDATE Giveaways SET announced=1,announcement_message_id=? WHERE id=?',
                                (announcement_id,row['id']))

    @tasks.loop(seconds=5)
    async def check_deadlines(self):
        try:
            await self.settle_due()
        except Exception:
            LOG.exception('Giveaway scheduler failed; will retry')

    @check_deadlines.before_loop
    async def before_deadlines(self):
        await self.bot.wait_until_ready()
