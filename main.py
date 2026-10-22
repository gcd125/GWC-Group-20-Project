import discord
import os

from dotenv import load_dotenv
from welcomemessage import send_welcome_message
from events import send_event_message

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

# --------------------------------------------------
# MAKE SURE BOT IS ON AND CONNECTED
# --------------------------------------------------

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


# --------------------------------------------------
# REAL MEMBER JOIN EVENT
# --------------------------------------------------

@client.event
async def on_member_join(member):

    channel = discord.utils.get(
        member.guild.text_channels,
        name="welcome"
    )

    if channel is None:
        return

    await send_welcome_message(
        channel,
        member
    )


# --------------------------------------------------
# TEMPORARY TEST COMMAND
# --------------------------------------------------

@client.event
async def on_message(message):

    # Prevent bot from responding to itself
    if message.author == client.user:
        return

    if message.content.lower() == "!testwelcome":

        await send_welcome_message(
            message.channel,
            message.author
        )

    elif message.content.lower() == "!testevent":

        await send_event_message(message.channel)


# --------------------------------------------------
# BOT TOKEN (hidden and need to reset)
# --------------------------------------------------

client.run(os.environ["DISCORD_TOKEN"]) # hide the bot token