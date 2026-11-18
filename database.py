"""Shared connection and registration-schema validation."""
from pathlib import Path
import sqlite3

def connect_database(path):
    # mode=rw prevents silently creating an empty database at a wrong path.
    db = sqlite3.connect(Path(path).expanduser().resolve().as_uri() + '?mode=rw', uri=True)
    db.row_factory = sqlite3.Row
    columns = {row[1] for row in db.execute('PRAGMA table_info(Members)')}
    required = {'member_id', 'first_name', 'member_dob', 'member_status', 'last_name', 'points_balance'}
    if not required <= columns:
        db.close()
        raise ValueError('Registration database needs Members with: ' + ', '.join(sorted(required)))
    return db
