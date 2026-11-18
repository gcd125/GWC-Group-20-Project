"""GWC bot startup. Each feature lives in its own module."""
import argparse
import datetime as dt
import getpass
import logging
import os
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

import certifi
from dotenv import load_dotenv

# Environment setup (must come before importing discord)
load_dotenv()
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import discord
from database import connect_database
from features.bot_commands import register_commands, sync_commands
from features.bot_events import register_events
from features.birthdays import BirthdayFeature, birthday_members, greeting
from features.leaderboard import LeaderboardFeature
from features.giveaways import GiveawayFeature
from features.welcome import WelcomeFeature
from features.member_links import initialize_links

LOG = logging.getLogger(__name__)


# --------------------------------------------------
# BOT SETUP
# --------------------------------------------------

class GWCBot(discord.Client):
    def __init__(self, db, channel_id, timezone, send_time, test_mode=False):
        # Needed to detect when a member joins
        intents = discord.Intents.default()
        intents.members = True

        # Needed for temporary message commands like !testwelcome
        intents.message_content = True

        super().__init__(intents=intents)

        # Settings the features can use
        self.db = db
        self.channel_id = channel_id
        self.timezone = timezone
        self.send_time = send_time
        self.test_mode = test_mode

        # Features
        self.birthdays = BirthdayFeature(self)
        self.leaderboard = LeaderboardFeature(self)
        self.giveaways = GiveawayFeature(self)
        self.welcome = WelcomeFeature(self)

        # Commands and events (the same two calls your old main made)
        self.tree = register_commands(self)
        register_events(self, self.tree)

    async def setup_hook(self):
        # Runs once when the bot starts
        initialize_links(self.db)
        self.welcome.start()
        await sync_commands(self, self.tree)
        self.birthdays.start()
        self.giveaways.start()

    async def close(self):
        # Runs when the bot shuts down
        self.welcome.stop()
        self.birthdays.stop()
        self.giveaways.stop()
        await super().close()


# --------------------------------------------------
# STARTUP HELPERS
# --------------------------------------------------

def read_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", metavar="YYYY-MM-DD",
                        help="Print birthday greetings without connecting to Discord")
    parser.add_argument("--test-mode", action="store_true",
                        help="Use gwc_test.db and turn off scheduled birthday posts")
    return parser, parser.parse_args()


def preview_birthdays(path, date_text):
    # Read-only, so nothing in the database changes
    uri = Path(path).expanduser().resolve().as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.row_factory = sqlite3.Row
    try:
        members = birthday_members(db, dt.date.fromisoformat(date_text))
        for member in members:
            print(greeting(member))
        if not members:
            print("No active member birthdays on this date.")
    finally:
        db.close()


# --------------------------------------------------
# START THE BOT
# --------------------------------------------------

def main():
    parser, args = read_arguments()
    logging.basicConfig(level=logging.INFO)

    # Which database: test file with --test-mode, otherwise the real one from .env
    if args.test_mode:
        path = str(Path(__file__).with_name("gwc_test.db"))
    else:
        path = os.environ.get("GWC_DATABASE_PATH")
    if not path:
        parser.error("Set GWC_DATABASE_PATH in your .env file")

    if args.preview:
        preview_birthdays(path, args.preview)
        return

    # Settings from the .env file
    token = os.environ.get("DISCORD_TOKEN")
    if not token and args.test_mode:
        token = getpass.getpass("Discord bot token (hidden): ").strip()
    if not token:
        parser.error("Set DISCORD_TOKEN in your .env file")

    channel = os.environ.get("GENERAL_CHANNEL_ID", "")
    if not args.test_mode and (not channel.isdigit() or int(channel) <= 0):
        parser.error("Set a valid numeric GENERAL_CHANNEL_ID in your .env file")

    timezone = ZoneInfo(os.environ.get("BIRTHDAY_TIMEZONE", "America/New_York"))
    send_time = dt.time.fromisoformat(os.environ.get("BIRTHDAY_TIME", "09:00"))
    if send_time.tzinfo is not None:
        parser.error("BIRTHDAY_TIME must be a local time such as 09:00")

    # Connect and run
    LOG.info("Using database: %s", Path(path).expanduser().resolve())
    db = connect_database(path)
    channel_id = None if args.test_mode else int(channel)

    try:
        GWCBot(db, channel_id, timezone, send_time, test_mode=args.test_mode).run(token)
    finally:
        db.close()


if __name__ == "__main__":
    main()