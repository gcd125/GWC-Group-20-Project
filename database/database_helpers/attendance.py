from database.database_helpers.events import get_connection, get_member


def register_for_event(member_id, event_id):
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO Event_Participation (member_id, event_id) VALUES (?, ?)",
        (member_id, event_id))
    registered = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return registered


def mark_present(member_id, event_id):
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute(
        """UPDATE Event_Participation SET member_attendance = 'present', point_balance = COALESCE(points_earned, 0) + ?
           WHERE member_id = ? AND event_id = ?""",
        (member_id, event_id))
    updated = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return updated


def record_attendance(event_id, discord_id, points):
    # Passcode check-in. Returns None if not a registered member,
    # True if newly marked present, False if already present.
    member = get_member(discord_id)
    if member is None:
        return None

    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO Event_Participation (member_id, event_id) VALUES (?, ?)",
        (member[0], event_id))
    cursor.execute(
        """UPDATE Event_Participation 
                SET member_attendance = 'present',
                point_balance = COALESCE(points_earned, 0) + ?
           WHERE member_id = ? AND event_id = ?
             AND (member_attendance IS NULL OR member_attendance != 'present')""",
        (points, member[0], event_id))
    newly_present = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return newly_present


def get_attendance_counts(event_id):
    connection = get_connection()

    cursor = connection.cursor()
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(CASE WHEN member_attendance = 'present'
            THEN 1 ELSE 0 END), 0)
        FROM Event_Participation WHERE event_id = ?
    """, (event_id))
    total, present = cursor.fetchone()

    connection.close()

    return total, present