# database.py
import sqlite3
from pathlib import Path

DB_PATH = Path("database/gwcbot.sql").parent / "gwcbot.sql"
if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found at {DB_PATH}")
else:
    print("we found it")
connection = sqlite3.connect(DB_PATH) 



def record_attendance(event_id: int, member_id: int) -> bool:
    cursor = connection.cursor()
    member_attendance = "present"
    cursor.execute(
        "SELECT 1 FROM Event_Participation WHERE event_id = ? AND member_id = ? AND member_attendance = ? and LIMIT 1",
        (event_id, member_id, member_attendance),
    )
    exists = cursor.fetchone() is not None
    if(exists): return False

    cursor.execute(
        "INSERT INTO Event_Participation (event_id, member_id, member_attendance) VALUES (?, ?, ?)",
        (event_id, member_id, member_attendance),
    )
    connection.commit()
    return True

