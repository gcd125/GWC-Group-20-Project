import sqlite3
from database.database_helpers.events import get_connection, get_member

def get_points(discord_id: int) -> int | None:
    try:
        with sqlite3.connect('database/gwcbot.db') as connection:
            result = connection.execute(
                """
                SELECT points_balance
                FROM Members
                WHERE discord_id = ?
                """,
                (str(discord_id),)
            ).fetchone()
        return result[0] if result else None
    except sqlite3.Error as error:
        print(f"Database error: {error}")
        return None

def get_leaderboard(limit: int = 10):
    try:
        with sqlite3.connect('database/gwcbot.db') as connection:
            return connection.execute(
                """
                SELECT full_name, points_balance
                FROM Members
                ORDER BY points_balance DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()
    except sqlite3.Error as error:
        print(f"Database error: {error}")
        return []

def add_points(points, discord_id):
    member = get_member(discord_id)
    if member is None:
        return None
    member_id = member[0]
    try:
        with sqlite3.connect('database/gwcbot.db') as connection:
            connection.execute(
                """
                UPDATE Members
                SET points_balance = COALESCE(points_balance, 0) + ?
                WHERE member_id = ?
                """,
                (points, member_id)
            )
    except sqlite3.Error as error:
        print(f"Database error: {error}")
        return []    