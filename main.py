import discord
from discord import app_commands

#enviornment setup
import os
from dotenv import load_dotenv

#calling other files
from bot.bot_commands import register_commands
from bot.bot_events import register_events

from database.database_setup.setup_database import init_db

init_db()

load_dotenv()
# --------------------------------------------------
# INTENTS / BOT SETUP
# --------------------------------------------------

functionalities = discord.Intents.default()

# Needed to detect when a member joins
functionalities.members = True

# Needed for temporary message commands like !testwelcome
functionalities.message_content = True


client = discord.Client(intents=functionalities)

tree = register_commands(client)
register_events(client, tree)




client.run(os.environ["DISCORD_TOKEN"]) # hide the bot token