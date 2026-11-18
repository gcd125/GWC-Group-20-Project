import sqlite3
  
def get_points(discord_id: int) -> int | None:
    try:
        with sqlite3.connect('gwcbot.db') as connection:
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
        with sqlite3.connect('gwcbot.db') as connection:
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