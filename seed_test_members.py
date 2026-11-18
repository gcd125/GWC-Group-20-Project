"""Create a NEW fictional birthday-test database; never overwrite an existing file."""
import argparse
import datetime as dt
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--database', type=Path, default=Path(__file__).with_name('gwc_test.db'))
parser.add_argument('--date', type=dt.date.fromisoformat, default=dt.datetime.now(ZoneInfo('America/New_York')).date())
args = parser.parse_args()
today = args.date
schema = Path(__file__).with_name('gwcdbbot.sql').read_text()
# Load the Members table used by the bot.
member_schema = schema.split(';', 1)[0] + ';'
rows = [
    (9001, 'member', 'Avery', 'Test', today.strftime('%m-%d'), 'Computer Science', None, 'active', 0),
    (9002, 'member', 'Jordan', 'Sample', (today + dt.timedelta(days=2)).strftime('%m-%d'), 'Information Technology', None, 'active', 0),
    (9003, 'member', 'Riley', 'Demo', (today + dt.timedelta(days=1)).strftime('%m-%d'), 'Computer Engineering', None, 'active', 0),
    (9004, 'member', 'Morgan', 'Fictional', today.strftime('%m-%d'), 'Mathematics', None, 'inactive', 0),
    (9005, 'member', 'Casey', 'Example', None, 'Computer Science', None, 'active', 0),
    (9006, 'member', 'Quinn', 'Test', '02-29', 'Data Science', None, 'active', 0),
]
# Exclusive creation prevents replacing any existing registrations.
with args.database.open('xb'):
    pass
with sqlite3.connect(args.database) as db:
    db.execute(member_schema)
    db.executemany('INSERT INTO Members VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', rows)
    db.executemany('UPDATE Members SET points_balance=? WHERE member_id=?', [(150,9001),(100,9002),(100,9003),(999,9004),(0,9005),(50,9006)])
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print(f'Created {args.database} with {len(rows)} fictional members; test date: {today}')
