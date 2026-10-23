import discord
import sqlite3

#----------------------------------------------
# DATABASE HELPERS
# --------------------------------------------------

def get_events():
    connection = sqlite3.connect("gwcbot.db")

    cursor = connection.cursor()
    cursor.execute("SELECT event_id, event_name FROM Events")

    events = cursor.fetchall()

    connection.close()

    return events

def get_event(event_id):
    connection = sqlite3.connect("gwcbot.db")

    cursor = connection.cursor()

    cursor.execute(
        "SELECT event_id, event_name FROM Events WHERE event_id = ?",
        (event_id,))


    event = cursor.fetchone()

    connection.close()

    return event
    

async def send_event_message(channel, event_id=1):

    event = get_event(event_id)

    if event is None:
        await channel.send("Event not found.")
        return

    event_name = event[1]

    # Event header
    embed = discord.Embed(
    title=f"💻 {event_name}",
    description="Join us for our upcoming event!",
    color=discord.Color.blue()
)
    # Event date
    embed.add_field(
    name="📅 Date",
    value="October 30, 2026",
    inline=False
    )

    # Event time
    embed.add_field(
    name="🕕 Time",
    value="6:00 pm",
    inline=False
    )

    # Event Location
    embed.add_field(
    name="📍 Location",
    value="Classroom Building 2, Room: 101 (CB2 101)",
    inline=False
    )

    await channel.send(embed=embed)