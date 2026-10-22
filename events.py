import discord

async def send_event_message(channel):

    embed = discord.Embed(
    title="💻 Girls Who Code Event",
    description="Join us for our upcoming event!",
    color=discord.Color.blue()
)

    await channel.send(embed=embed)