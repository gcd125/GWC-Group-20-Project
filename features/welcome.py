"""Welcome preview and private member registration."""
import datetime as dt
import logging
import os
import sqlite3
import secrets
import discord

LOG = logging.getLogger(__name__)
FOOTER = 'Girls Who Code @ UCF 🤍 Code • Connect • Create'


def register_member(db, guild_id, discord_id, first_name, last_name, major, birthday='', phone=''):
    first_name, last_name, major = (' '.join(value.split()) for value in (first_name, last_name, major))
    if any(not value or len(value) > 100 for value in (first_name, last_name, major)):
        raise ValueError('First name, last name, and major must each contain 1–100 characters.')
    birthday = birthday.strip()
    if birthday:
        try:
            # A leap year allows February 29 without collecting a birth year.
            parsed = dt.datetime.strptime('2000/' + birthday, '%Y/%m/%d')
            birthday = parsed.strftime('%m-%d')
        except ValueError:
            raise ValueError('Enter your birthday as MM/DD, for example 11/12, or leave it blank.') from None
    phone = phone.strip() or None
    if phone and len(phone) > 30:
        raise ValueError('Phone number must be 30 characters or fewer.')
    with db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT member_id FROM Member_Discord_Links WHERE guild_id=? AND discord_id=?',
                              (str(guild_id),str(discord_id))).fetchone()
        if existing:
            return existing[0], False
        # The write lock covers selection and insertion, including other processes.
        used_ids = {row[0] for row in db.execute('SELECT member_id FROM Members')}
        available_ids = [value for value in range(1, 10000) if value not in used_ids]
        if not available_ids:
            raise ValueError('All 9,999 member IDs are in use. Please contact a club organizer.')
        member_id = secrets.choice(available_ids)
        try:
            db.execute('''INSERT INTO Members
                (member_id,member_role,first_name,last_name,member_dob,major,phone_number,member_status,points_balance)
                VALUES (?,'member',?,?,?,?,?,'active',0)''', (member_id,first_name,last_name,birthday or None,major,phone))
            db.execute('INSERT INTO Member_Discord_Links (guild_id,discord_id,member_id) VALUES(?,?,?)',
                       (str(guild_id),str(discord_id),member_id))
        except sqlite3.IntegrityError:
            raise ValueError('This registration conflicts with an existing record. Ask a club organizer to link your existing registration.') from None
    return member_id, True


def welcome_embed(user_id):
    embed = discord.Embed(title='✨ Welcome to Girls Who Code @ UCF ✨', colour=0x82A7DB,
        description=(f'Hey <@{user_id}>!\n\n'
            '🌸 Read the rules ✨\n🌸 Introduce yourself ✨\n🌸 Keep an eye on announcements ✨\n'
            '🌸 Ask for help anytime ✨\n🌸 Socialize, learn, and grow together! 🤍\n\n'
            '**Before getting started, please fill your member registration.**\n\n'
            '*Your responses are private and are collected only for the Girls Who Code @ UCF '
            'club database. If you provide a birthday, we will celebrate it with your first name in #general. '
            'Your other registration details will not be shared with other members.*'))
    embed.set_footer(text=FOOTER)
    return embed


def public_welcome_embed(user_id):
    embed = discord.Embed(
        title='✨ Welcome to Girls Who Code @ UCF ✨', colour=0x82A7DB,
        description=(f'Hey <@{user_id}>, welcome to the GWC family! 💙\n\n'
                     '🌸 A little code, a lot of friendship, and a place to grow together.\n'
                     '**Everybody say hiiii!** 👋✨\n\n'
                     'Your next adventure starts here. 🤍'))
    embed.set_footer(text=FOOTER)
    return embed


class RegistrationPromptView(discord.ui.View):
    def __init__(self, feature):
        super().__init__(timeout=None)
        self.feature = feature

    @discord.ui.button(label='Register privately 🤍', style=discord.ButtonStyle.success,
                       custom_id='gwc:registration:private:v1')
    async def open_private(self, interaction, button):
        if interaction.guild is None or interaction.user.bot:
            await interaction.response.send_message('Please register from the club server.', ephemeral=True)
            return
        recipient = self.feature.bot.db.execute(
            'SELECT recipient_id FROM Welcome_Commands WHERE response_id=?',
            (str(interaction.message.id),)).fetchone()
        if not recipient or recipient[0] != str(interaction.user.id):
            await interaction.response.send_message(
                'This welcome is for another member. Use /registration to open your own registration. 💙',
                ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        delivered = await self.feature.send_registration_dm(
            f'interaction:{interaction.id}', interaction.user, interaction.guild)
        await interaction.followup.send(
            'Your private registration card is in your DMs! 💙' if delivered else
            'Enable DMs from server members, then use /registration to try again. 💙', ephemeral=True)



class RegistrationModal(discord.ui.Modal, title='Member Registration'):
    first_name = discord.ui.TextInput(label='First name', max_length=100)
    last_name = discord.ui.TextInput(label='Last name', max_length=100)
    major = discord.ui.TextInput(label='Major', max_length=100)
    birthday = discord.ui.TextInput(label='Birthday (MM/DD)', placeholder='11/12', required=False, max_length=5)
    phone = discord.ui.TextInput(label='Phone number (optional)', required=False, max_length=30)

    def __init__(self, feature, guild=None, user_id=None):
        super().__init__(timeout=600)
        self.feature = feature
        self.guild = guild
        self.user_id = user_id

    async def on_submit(self, interaction):
        guild = self.guild or interaction.guild
        if guild is None or interaction.user.bot or (self.user_id is not None and interaction.user.id != self.user_id):
            await interaction.response.send_message('Register from your own registration card.', ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        created = False
        try:
            member_id, created = register_member(self.feature.bot.db, guild.id, interaction.user.id,
                str(self.first_name),str(self.last_name),str(self.major),str(self.birthday),str(self.phone))
            text = (f'You’re officially part of the GWC family! 💙✨\n\n'
                    f'Your member ID is **{member_id:04d}**.\n\n'
                    '🌸 Join us at club events\n'
                    '⭐ Check your points on the leaderboard\n'
                    '🎁 Enter our giveaways\n'
                    '💻 Make friends, learn together, and enjoy so much more!\n\n'
                    'We’re so happy you’re here. Let’s code, connect, and create! 🤍'
                    if created else 'Your Discord account is already linked to a registration. No information was changed. 💙')
        except ValueError as error:
            text = str(error)
        except Exception:
            # Keep personal details out of logs.
            LOG.error('Could not save member registration')
            text = 'Registration could not be saved. Please try again or ask a club organizer for help.'
        await interaction.followup.send(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        if created:
            try:
                await self.feature.bot.birthdays.handle_registration(member_id, guild)
            except Exception:
                LOG.exception('Registration saved, but birthday delivery failed for member %s', member_id)


class RegistrationView(discord.ui.View):
    def __init__(self, feature):
        super().__init__(timeout=None)
        self.feature = feature

    @discord.ui.button(label='Start Registration 🤍', style=discord.ButtonStyle.success,
                       custom_id='gwc:registration:start:v1')
    async def register(self, interaction, button):
        if interaction.guild is not None:
            await interaction.response.send_message(
                'Registration has moved to DMs! Use /registration to receive your private card. 💙', ephemeral=True)
            return
        guild = interaction.guild
        if guild is None:
            row = self.feature.bot.db.execute(
                'SELECT guild_id, recipient_id FROM Registration_DMs WHERE message_id=?',
                (str(interaction.message.id),)).fetchone()
            if row and row['recipient_id'] == str(interaction.user.id):
                guild = self.feature.bot.get_guild(int(row['guild_id']))
        if guild is None or interaction.user.bot:
            await interaction.response.send_message('Use /registration in the club server to request a new private card.', ephemeral=True)
            return
        existing = self.feature.bot.db.execute('SELECT member_id FROM Member_Discord_Links WHERE guild_id=? AND discord_id=?',
            (str(guild.id),str(interaction.user.id))).fetchone()
        if existing:
            await interaction.response.send_message('Your Discord account is already linked to a registration. No need to register again! 💙', ephemeral=True)
            return
        await interaction.response.send_modal(RegistrationModal(self.feature, guild, interaction.user.id))


class WelcomeFeature:
    def __init__(self, bot):
        self.bot = bot
        self.view = None
        self.prompt_view = None

    def start(self):
        self.initialize_command_history()
        self.view = RegistrationView(self)
        self.bot.add_view(self.view)
        self.prompt_view = RegistrationPromptView(self)
        self.bot.add_view(self.prompt_view)

    def stop(self):
        if self.view:
            self.view.stop()
        if self.prompt_view:
            self.prompt_view.stop()

    def initialize_command_history(self):
        with self.bot.db:
            self.bot.db.execute("""CREATE TABLE IF NOT EXISTS Welcome_Commands (
                message_id TEXT PRIMARY KEY,
                response_id TEXT,
                recipient_id TEXT,
                created_at INTEGER NOT NULL DEFAULT (unixepoch())
            )""")
            self.bot.db.execute("""CREATE TABLE IF NOT EXISTS Registration_DMs (
                event_id TEXT PRIMARY KEY, guild_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL, message_id TEXT UNIQUE
            )""")
            columns = {row[1] for row in self.bot.db.execute("PRAGMA table_info(Welcome_Commands)")}
            if "recipient_id" not in columns:
                self.bot.db.execute("ALTER TABLE Welcome_Commands ADD COLUMN recipient_id TEXT")

    async def handle_join(self, member):
        if member.bot:
            return
        joined_at = member.joined_at.isoformat() if member.joined_at else 'unknown'
        event_id = f'join:{member.guild.id}:{member.id}:{joined_at}'
        await self.send_registration_dm(event_id, member, member.guild)
        configured_id = os.environ.get('WELCOME_CHANNEL_ID', '').strip()
        if configured_id:
            if not configured_id.isdigit():
                LOG.error('WELCOME_CHANNEL_ID must be a numeric channel ID')
                return
            channel = member.guild.get_channel(int(configured_id))
        else:
            channels = [channel for channel in member.guild.text_channels if channel.name == 'welcome']
            channel = channels[0] if len(channels) == 1 else None
        if channel is None:
            LOG.error('No unique welcome channel in guild %s. Set WELCOME_CHANNEL_ID; members can use /registration.', member.guild.id)
            return
        # A rejoin gets a new event ID.
        joined_at = member.joined_at.isoformat() if member.joined_at else 'unknown'
        event_id = f'join:{member.guild.id}:{member.id}:{joined_at}'
        try:
            await self.send_welcome(event_id, channel, member.id)
        except Exception:
            LOG.exception('Welcome delivery failed in guild %s; /registration is available.', member.guild.id)

    async def handle_message(self, message):
        delivered = await self.send_registration_dm(str(message.id), message.author, message.guild)
        if delivered is False:
            await message.channel.send(
                'I couldn’t send your registration DM. Enable direct messages from server members, then try /registration again. 💙',
                allowed_mentions=discord.AllowedMentions.none())

    async def send_registration_dm(self, event_id, user, guild):
        with self.bot.db:
            claimed = self.bot.db.execute(
                'INSERT OR IGNORE INTO Registration_DMs(event_id,guild_id,recipient_id) VALUES(?,?,?)',
                (event_id,str(guild.id),str(user.id))).rowcount
        if not claimed:
            return None
        try:
            message = await user.send(embed=welcome_embed(user.id), view=RegistrationView(self),
                                      allowed_mentions=discord.AllowedMentions.none())
        except (discord.Forbidden, discord.NotFound):
            with self.bot.db:
                self.bot.db.execute('DELETE FROM Registration_DMs WHERE event_id=?', (event_id,))
            LOG.warning('Registration DM blocked; member can enable DMs and use /registration')
            return False
        except Exception:
            LOG.exception('Registration DM delivery unresolved; use a new /registration command to retry')
            return False
        with self.bot.db:
            self.bot.db.execute('UPDATE Registration_DMs SET message_id=? WHERE event_id=?',
                                (str(message.id),event_id))
        return True

    async def send_welcome(self, event_id, channel, user_id):
        # Claim before sending to prevent duplicate replies.
        with self.bot.db:
            claimed = self.bot.db.execute(
                'INSERT OR IGNORE INTO Welcome_Commands(message_id,recipient_id) VALUES(?,?)',
                (event_id,str(user_id))
            ).rowcount
        if not claimed:
            LOG.info('Skipped repeated welcome command %s', event_id)
            return
        try:
            response = await channel.send(
                embed=public_welcome_embed(user_id),
                allowed_mentions=discord.AllowedMentions.none()
            )
        except (discord.Forbidden, discord.NotFound):
            # Discord definitively rejected the send, so a retry is safe.
            with self.bot.db:
                self.bot.db.execute('DELETE FROM Welcome_Commands WHERE message_id=?', (event_id,))
            raise
        # Keep the claim if a network response is lost: the send may have succeeded.
        with self.bot.db:
            self.bot.db.execute(
                'UPDATE Welcome_Commands SET response_id=? WHERE message_id=?',
                (str(response.id), str(event_id))
            )
        LOG.info('Welcome command %s replied with message %s', event_id, response.id)
