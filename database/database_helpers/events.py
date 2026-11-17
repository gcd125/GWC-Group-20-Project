import discord
import sqlite3

#----------------------------------------------
# DATABASE HELPERS
# --------------------------------------------------
connection = sqlite3.connect("gwcbot.db")


class NewEvent:
    def __init__(self, name, type_id, organizer_id, points, date,
                 start_time, end_time, passcode, opens_at, closes_at):
        self.name = name
        self.type_id = type_id
        self.organizer_id = organizer_id
        self.points = points
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.passcode = passcode
        self.opens_at = opens_at
        self.closes_at = closes_at

        if self.end_time <= self.start_time:
            raise ValueError("Event must end after it starts.")
        if self.points < 0:
            raise ValueError("Points can't be negative.")
        if not self.passcode.strip():
            raise ValueError("Passcode can't be empty.")
        



def create_event(event: NewEvent) -> bool:
    connection.execute("PRAGMA busy_timeout = 10000")
    cursor = connection.cursor()
    cursor.execute(
            """INSERT INTO Events
               (event_name, 
               event_type_id, 
               event_organizer_id,
                event_points,
                event_start_time, 
                event_end_time, 
                event_passcode, 
                event_attendance_opens_at, 
                event_attendance_closes_at
                )
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event.name,
             event.type_id, 
             event.organizer_id,
             event.points, 
             event.start_time, 
             event.end_time,
             event.passcode.strip().lower(), 
             event.opens_at, 
             event.closes_at),
        )
    connection.commit()
    
    return True

def get_events():

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

def get_active_event(passcode: str, now: int):
    connection = sqlite3.connect("gwcbot.db")
    
    cursor = connection.cursor()
    
    return cursor.execute(
        """SELECT id, name FROM events
           WHERE passcode = ? AND opens_at <= ? AND closes_at >= ?""",
        (passcode, now, now),
    ).fetchone()
    

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