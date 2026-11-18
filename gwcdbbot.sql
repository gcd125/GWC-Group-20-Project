CREATE TABLE Members (
    member_id INTEGER PRIMARY KEY,
    member_role TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    member_dob TEXT,
    major TEXT NOT NULL,
    phone_number TEXT UNIQUE,
    member_status TEXT DEFAULT 'active',
    points_balance INTEGER NOT NULL DEFAULT 0
);
