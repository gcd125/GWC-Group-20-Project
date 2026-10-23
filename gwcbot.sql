CREATE TABLE Members (
    member_id INTEGER PRIMARY KEY,
    member_role TEXT DEFAULT 'member',
    discord_id TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    member_dob TEXT,
    ucf_email TEXT UNIQUE,
    major TEXT,
    phone_number TEXT UNIQUE,
    member_bio TEXT,
    additional_info TEXT,
    member_status TEXT DEFAULT 'active',
    points_balance INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE Event_Types (
    type_id INTEGER PRIMARY KEY,
    type_name TEXT NOT NULL UNIQUE
);

INSERT INTO Event_Types (type_name)
VALUES
    ('Workshop'),
    ('GBM'),
    ('Social'),
    ('Hackathon'),
    ('Projects'),
    ('Volunteering'),
    ('Fundraiser'),
    ('Other');

CREATE TABLE Events (
    event_id INTEGER PRIMARY KEY,
    event_name TEXT NOT NULL,
    event_type_id INTEGER NOT NULL, 
    event_organizer INTEGER,
    event_points INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (event_organizer) REFERENCES Members(member_id), -- event organizer can only be creating by assigning at least a member
    FOREIGN KEY (event_type_id) REFERENCES Event_Types(type_id) -- corelate to previous event type table
);

CREATE TABLE Event_Participation ( -- integration of members + events
    participation_id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    member_attendance TEXT DEFAULT 'not present',
    FOREIGN KEY (member_id) REFERENCES Members(member_id), -- corelate to previous tables
    FOREIGN KEY (event_id) REFERENCES Events(event_id),

    UNIQUE (member_id, event_id),

    CHECK (member_attendance IN ('not present', 'present'))
);

-- Member info querie: Pull all info about the member (easier for board members)


-- input all info from the event (querie):


-- Events.event_name will be assigned at creation
-- Events.event_organizer will be assigned by the creator (whoever gives the command?) -> 
-- Events.event_points will be assigned at creation
