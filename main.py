import discord
import sqlite3
import os
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

from points import get_points
from points import get_leaderboard
from welcomemessage import send_welcome_message

DISCORD_GUILD_ID = discord.Object(id=int(os.environ["DISCORD_GUILD_ID"]))

# --------------------------------------------------
# INTENTS / BOT SETUP
# --------------------------------------------------

functionalities = discord.Intents.default()

# Needed to detect when a member joins
functionalities.members = True

# Needed for temporary message commands like !testwelcome
functionalities.message_content = True


client = commands.Bot(command_prefix='!', intents=functionalities)


# --------------------------------------------------
# MAKE SURE BOT IS ON AND CONNECTED
# --------------------------------------------------

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    
    synced = await client.tree.sync(guild=DISCORD_GUILD_ID)
    print(f"Synced {len(synced)} command(s).")


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
        await client.process_commands(message)
        
# --------------Points Command---------------------

@client.tree.command(
    name="points", 
    description="View your points", 
    guild = DISCORD_GUILD_ID
)
  
async def points(interaction: discord.Interaction):
    await interaction.response.defer() 
    user_points = get_points(interaction.user.id)
    
    if user_points is None:
        await interaction.edit_original_response(
            content="You are not registered yet."
        )
        return
    await interaction.edit_original_response(
        content=f"You have {user_points} points."
    )

# --------------Leaderboard Command---------------------

@client.tree.command(
    name="leaderboard", 
    description="View the points leaderboard", 
    guild = DISCORD_GUILD_ID
)
async def leaderboard(interaction: discord.Interaction):
    members = get_leaderboard()
    
    if not members:
        await interaction.response.send_message(
            "No registered members yet."
        )
        return
    lines = [
        f"**{place}. {name}** {points} points"
        for place, (name, points) in enumerate(members, start=1)
    ]
    await interaction.response.send_message(
        "Points Leaderboard:\n" + "\n".join(lines)
    )


# --------------------------------------------------
# BOT TOKEN (hidden and need to reset)
# --------------------------------------------------

client.run(os.environ["DISCORD_TOKEN"]) # hide the bot token