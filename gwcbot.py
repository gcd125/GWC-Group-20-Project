"""GWC bot startup and routing; each feature lives in its own module."""
import argparse
import datetime as dt
import logging
import getpass
import os
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

import certifi

# Configure CA roots before Discord/aiohttp initializes its TLS contexts.
# Preserve an explicitly configured trust bundle (e.g. a campus CA).
os.environ.setdefault('SSL_CERT_FILE', certifi.where())

import discord
from bot_commands import register_commands, sync_commands
from bot_events import register_events
from features.birthdays import BirthdayFeature, birthday_members, greeting
from database import connect_database
from features.leaderboard import LeaderboardFeature
from features.giveaways import GiveawayFeature
from features.welcome import WelcomeFeature
from features.member_links import initialize_links

LOG = logging.getLogger(__name__)

class GWCBot(discord.Client):
    def __init__(self, db, channel_id, timezone, send_time, test_mode=False):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.db, self.channel_id = db, channel_id
        self.timezone, self.send_time = timezone, send_time
        self.test_mode = test_mode
        self.birthdays = BirthdayFeature(self)
        self.leaderboard = LeaderboardFeature(self)
        self.giveaways = GiveawayFeature(self)
        self.welcome = WelcomeFeature(self)
        self.tree = register_commands(self)
        register_events(self, self.tree)

    async def setup_hook(self):
        initialize_links(self.db)
        self.welcome.start()
        await sync_commands(self, self.tree)
        self.birthdays.start()
        self.giveaways.start()

    async def close(self):
        self.welcome.stop()
        self.birthdays.stop()
        self.giveaways.stop()
        await super().close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', metavar='YYYY-MM-DD', help='Print greetings without connecting to Discord or recording sends')
    parser.add_argument('--test-mode', action='store_true', help='Use gwc_test.db; disable scheduled birthday posts')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    path = str(Path(__file__).with_name('gwc_test.db')) if args.test_mode else os.environ.get('GWC_DATABASE_PATH')
    if not path:
        parser.error('Set GWC_DATABASE_PATH to the existing SQLite registration database')
    if args.preview:
        # Read-only previews must not create or change delivery records.
        db = sqlite3.connect(Path(path).expanduser().resolve().as_uri() + '?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        try:
            members = birthday_members(db, dt.date.fromisoformat(args.preview))
            for member in members:
                print(greeting(member))
            if not members:
                print('No active member birthdays on this date.')
        finally:
            db.close()
        return
    token = os.environ.get('DISCORD_TOKEN')
    channel = os.environ.get('GENERAL_CHANNEL_ID', '')
    if not token and args.test_mode:
        token = getpass.getpass('Discord bot token (hidden): ').strip()
    if not token:
        parser.error('Set DISCORD_TOKEN')
    if not args.test_mode and (not channel.isdigit() or int(channel) <= 0):
        parser.error('Set a valid numeric GENERAL_CHANNEL_ID')
    timezone = ZoneInfo(os.environ.get('BIRTHDAY_TIMEZONE', 'America/New_York'))
    send_time = dt.time.fromisoformat(os.environ.get('BIRTHDAY_TIME', '09:00'))
    if send_time.tzinfo is not None:
        parser.error('BIRTHDAY_TIME must be a local time such as 09:00')
    db = connect_database(path)
    try:
        GWCBot(db, None if args.test_mode else int(channel), timezone, send_time, test_mode=args.test_mode).run(token)
    finally:
        db.close()


if __name__ == '__main__':
    main()
