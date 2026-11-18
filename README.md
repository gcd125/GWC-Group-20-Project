# GWC-Group-20-Project
Girls Who Code Fall 2026 Project

# Project Name
GWC Discord Bot (Working Title)

## About
Our project is a Discord bot developed using Python to improve the functionality and user experience of our Girls Who Code Discord server.

The goal is to create a beginner-friendly, practical tool that helps members navigate the server, access important information, and stay connected with club activities.

## Team
- Gabriella Delgadillo - Project Mentor
- Melanie — Team Member
- Gabriela — Team Member
- Member 3 — Team Member

## Technologies
- Python

## How to Run the Project
Requires Python 3.13. Run one bot process per Discord application; teammates must
stop older copies or duplicate public welcome cards can still appear.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed_test_members.py
python bot.py --test-mode
```

The test database contains fictional members. The startup prompts privately for
DISCORD_TOKEN if it is not exported. Never commit tokens or real database files.
Enable Server Members Intent and Message Content Intent in the Developer Portal.
Install the application with bot and applications.commands scopes. Give it View
Channel, Send Messages and Embed Links permissions.

- `/registration`: DM-only registration card, with a private command acknowledgement.
- `/giveaway`: private creation controls; the giveaway itself posts in the channel.
- Joining: public greeting in #welcome without buttons plus a separate registration DM.
- Registration links the member to giveaways, assigns a random unused 0001–9999 ID,
  and sends a same-day birthday greeting in #general.
- Existing `!leaderboard`, `!testbirthday`, and `!linkmember` remain available in this
  source. Other slash commands maintained elsewhere are not overwritten by startup.

Startup upserts only /registration and /giveaway. Global commands may take time to
appear in Discord. Do not run an older bot process with the same token.

For production, create an empty database using gwcdbbot.sql, export
GWC_DATABASE_PATH, DISCORD_TOKEN, and GENERAL_CHANNEL_ID, then run python bot.py.
Optional variables: WELCOME_CHANNEL_ID, BIRTHDAY_TIMEZONE (America/New_York),
BIRTHDAY_TIME (09:00), GIVEAWAY_HOST_ROLE_ID. Environment variables must be exported;
.env files are not automatically loaded. Test mode disables daily birthday scheduling,
but immediate registration birthdays still send.

Run `python -m unittest discover -v` for bot tests.

The `dashboard/` directory contains the GWC Insights website source and its
read-only export/sync tools. See dashboard/README.md for its separate build and
hosting setup. Copying the source to GitHub does not grant access to the existing
owner-private hosted dashboard or move the live database online.

## Project Goals
Develop a functional Discord bot using Python.
Improve accessibility to information within our Girls Who Code server.

## Files

- `bot.py`: entry point; `gwcbot.py`: client and commands.
- `welcome.py`, `birthdays.py`, `giveaways.py`, `leaderboard.py`: features.
- `database.py`, `member_links.py`, `gwcdbbot.sql`: database access and schema.
- `test_*.py`: tests.
- `dashboard/`: Insights website and export tools.
- `archive/early-registration/`: old prototype, kept for reference.

See [feature notes](docs/features.md) for registration, birthdays and giveaways.
