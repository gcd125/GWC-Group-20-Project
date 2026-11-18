import discord
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

#----------------------------------------------
# DATABASE HELPERS
# --------------------------------------------------
DATABASE = "database/gwcbot.db"
EASTERN = ZoneInfo("America/New_York")


def get_connection():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def setup_events_database():
    # Keep the existing tables and records. Add only fields needed for events.
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(Events)")
    columns = {column[1] for column in cursor.fetchall()}

    if not columns:
        connection.close()
        raise RuntimeError("Events table not found. Set up gwcbot.db first.")

    additions = {
        "event_date": "TEXT",
        "event_location": "TEXT",
        "reminder_channel_id": "TEXT",
        "reminder_sent": "INTEGER NOT NULL DEFAULT 0"
    }
    for name, definition in additions.items():
        if name not in columns:
            cursor.execute(f"ALTER TABLE Events ADD COLUMN {name} {definition}")

    connection.commit()
    connection.close()


class NewEvent:
    def __init__(self, name, type_id, organizer_id, points, date,
                 start_time, end_time, passcode, opens_at, closes_at,
                 location, reminder_channel_id):
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
        self.location = location
        self.reminder_channel_id = reminder_channel_id

        if self.end_time <= self.start_time:
            raise ValueError("Event must end after it starts.")
        if self.points < 0:
            raise ValueError("Points can't be negative.")
        if not self.passcode.strip():
            raise ValueError("Passcode can't be empty.")


def create_event(event: NewEvent) -> int:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
            """
            INSERT INTO Events(
                event_name,
                event_type_id,
                event_organizer_id,
                event_points,
                event_date,
                event_start_time,
                event_end_time,
                event_passcode,
                event_attendance_opens_at,
                event_attendance_closes_at,
                event_location,
                reminder_channel_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.name,
                event.type_id,
                event.organizer_id,
                event.points,
                event.date,
                event.start_time,
                event.end_time,
                event.passcode.strip().lower(),
                event.opens_at,
                event.closes_at,
                event.location,
                event.reminder_channel_id,
            ),
    )
    event_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return event_id


def get_events():
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute("""
        SELECT event_id, event_name, event_date, event_start_time, event_location
        FROM Events
        ORDER BY event_start_time
    """)

    events = cursor.fetchall()

    connection.close()

    return events


def get_event(event_id):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """SELECT event_id, event_name, event_date, event_start_time,
                  event_location, event_points
           FROM Events WHERE event_id = ?""",
        (event_id,))

    event = cursor.fetchone()

    connection.close()

    return event


def get_active_event(passcode: str, now: int):
    connection = get_connection()

    cursor = connection.cursor()

    event = cursor.execute(
        """SELECT event_id, event_name FROM Events
           WHERE event_passcode = ? AND event_attendance_opens_at <= ? AND event_attendance_closes_at >= ?""",
        (passcode, now, now),
    ).fetchone()

    connection.close()

    return event


def get_event_type(type_name):
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute(
        "SELECT type_id FROM Event_Types WHERE LOWER(type_name) = LOWER(?)",
        (type_name,))

    event_type = cursor.fetchone()

    connection.close()

    return event_type


def get_event_type_names():
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute("SELECT type_name FROM Event_Types ORDER BY type_id")

    names = [row[0] for row in cursor.fetchall()]

    connection.close()

    return names


def get_member(discord_id):
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute(
        "SELECT member_id FROM Members WHERE discord_id = ?",
        (str(discord_id),))

    member = cursor.fetchone()

    connection.close()

    return member


def get_pending_reminders():
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute("""
        SELECT event_id, event_name, event_date, event_start_time, reminder_channel_id
        FROM Events
        WHERE reminder_sent = 0 AND event_start_time IS NOT NULL
    """)

    events = cursor.fetchall()

    connection.close()

    return events


def mark_reminder_sent(event_id):
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute("UPDATE Events SET reminder_sent = 1 WHERE event_id = ?", (event_id,))

    connection.commit()
    connection.close()


# --------------------------------------------------
# TIME HELPERS
# --------------------------------------------------

def parse_eastern(date, time):
    # "2026-11-20" + "18:30" -> Eastern datetime, or raises ValueError.
    value = datetime.strptime(
        f"{date} {time}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=EASTERN)
    # Catch nonexistent local times during the spring DST change.
    if value.astimezone(ZoneInfo("UTC")).astimezone(EASTERN).replace(tzinfo=None) != value.replace(tzinfo=None):
        raise ValueError("Invalid local time")
    return value


def event_start(event):
    # Older rows may not have a start time yet.
    if not event[3]:
        return None
    return datetime.fromtimestamp(event[3], EASTERN)


def format_time(start):
    if start is None:
        return "Not set"
    return start.strftime("%I:%M %p").lstrip("0")


# --------------------------------------------------
# EVENT MESSAGE
# --------------------------------------------------

async def send_event_message(channel, event_id=1):

    event = get_event(event_id)

    if event is None:
        await channel.send("Event not found.")
        return

    event_id, event_name, date, start_time, location, points = event
    start = event_start(event)

    # Event header
    embed = discord.Embed(
    title=f"💻 {event_name}",
    description="Join us for our upcoming event!",
    color=discord.Color.blue()
)
    # Event date
    embed.add_field(
    name="📅 Date",
    value=date or "Not set",
    inline=False
    )

    # Event time
    embed.add_field(
    name="🕕 Time (Eastern)",
    value=format_time(start),
    inline=False
    )

    # Event Location
    embed.add_field(
    name="📍 Location",
    value=location or "Not set",
    inline=False
    )

    # Event points
    embed.add_field(
    name="⭐ Points",
    value=str(points),
    inline=False
    )

    embed.set_footer(text=f"Event ID: {event_id} • /event-register to sign up")

    await channel.send(embed=embed)