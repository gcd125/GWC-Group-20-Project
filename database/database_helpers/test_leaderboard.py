import sqlite3

with sqlite3.connect('leaderboard_test.db') as connection:
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS Members (
        member_id INTEGER PRIMARY KEY,
        discord_id TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        points_balance INTEGER NOT NULL DEFAULT 0
    );

    DELETE FROM Members;
    INSERT INTO Members (discord_id, full_name, points_balance)
    VALUES
        ('test-001', 'Grace Hopper', 150),
        ('test-002', 'Malala Yousafzai', 100),
        ('test-003', 'Ariana Grande', 75),
        ('test-004', 'Miles Davis', 25);
    """)

print("Test leaderboard database created.")