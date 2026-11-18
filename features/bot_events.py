import discord

#enviornment setup
import os
from dotenv import load_dotenv
load_dotenv()

from database.database_helpers.welcomemessage import send_welcome_message
from database.database_helpers.events import send_event_message


def register_events(client, tree):
    GUILD_ID = discord.Object(id=os.environ["GUILD_ID"])


    @client.event
    async def on_ready():
        tree.copy_global_to(guild=GUILD_ID)
        await tree.sync(guild=GUILD_ID)
        print(f"Logged in as {client.user}")

    @client.event
    async def on_member_join(member):
        channel = discord.utils.get(
            member.guild.text_channels,
            name="welcome",
        )

        if channel is not None:
            await send_welcome_message(channel, member)

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        command = message.content.lower()

        if command == "!testwelcome":
            await send_welcome_message(message.channel, message.author)
        elif command == "!testevent":
            await send_event_message(message.channel)