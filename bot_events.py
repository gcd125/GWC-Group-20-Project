import discord

from specific_tasks.welcomemessage import send_welcome_message
from specific_tasks.events import send_event_message


def register_events(client):
    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")

    # @client.event
    # async def on_member_join(member):
    #     channel = discord.utils.get(
    #         member.guild.text_channels,
    #         name="welcome",
    #     )

    #     if channel is not None:
    #         await send_welcome_message(channel, member)

    # @client.event
    # async def on_message(message):
    #     if message.author == client.user:
    #         return

    #     command = message.content.lower()

    #     if command == "!testwelcome":
    #         await send_welcome_message(message.channel, message.author)
    #     elif command == "!testevent":
    #         await send_event_message(message.channel)