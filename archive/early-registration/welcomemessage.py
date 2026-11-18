import discord

from registration import RegistrationView


async def send_welcome_message(channel, member):


    thumbnail = discord.File(
        "Visuals/gwc_thumbnail.png",
        filename="gwc_thumbnail.png"
    )

    embed = discord.Embed(
        title="✨ Welcome to Girls Who Code @ UCF ✨",
        description=(
            f"Hey {member.mention}!\n\n"

            "🌸 Read the rules ✨\n"
            "🌸 Introduce yourself ✨\n"
            "🌸 Keep an eye on announcements ✨\n"
            "🌸 Ask for help anytime ✨\n"
            "🌸 Socialize, learn, and grow together! 🤍\n\n"

            "**Before getting started, please fill your member registration.**\n\n"

            "*Your responses are private and are collected only "
            "for the Girls Who Code @ UCF club database. "
            "They will not be displayed to or shared with other members.*"
        ),

        color=discord.Color.from_rgb(
            120,
            160,
            220
        )
    )

    embed.set_thumbnail(
        url="attachment://gwc_thumbnail.png"
    )

    embed.set_image(
        url="attachment://welcome_banner.png"
    )

    embed.set_footer(
        text="Girls Who Code @ UCF 🤍 Code • Connect • Create"
    )

    await channel.send(
        files=[thumbnail],
        embed=embed,
        view=RegistrationView(member.id)
    )