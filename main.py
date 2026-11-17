import discord

#enviornment setup
import os
from dotenv import load_dotenv

#calling other files
from bot_events import register_events

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

register_events(client)

client.run(os.environ["DISCORD_TOKEN"]) # hide the bot token