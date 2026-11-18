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
```

Before the first test run, create an empty `gwc_test.db` from `gwcdbbot.sql`:

```sh
python - <<'PYTHON'
from pathlib import Path
import sqlite3

path = Path("gwc_test.db")
with path.open("xb"):
    pass
with sqlite3.connect(path) as db:
    db.executescript(Path("gwcdbbot.sql").read_text())
PYTHON
```

This refuses to overwrite an existing file. Skip this step if your test database
already exists. Then run `python bot.py --test-mode` and use `/registration` with
fictional details to create test members.

The startup prompts privately for
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

Run `python -m unittest discover -s tests -v` from the project root for all bot and analytics tests.

The `dashboard/` directory contains the GWC Insights website source and its
read-only export/sync tools. Copying the source to GitHub does not grant access to the existing
owner-private hosted dashboard or move the live database online.

## Project Goals
Develop a functional Discord bot using Python.
Improve accessibility to information within our Girls Who Code server.

## Files

- `bot.py`: entry point; `gwcbot.py`: client setup and feature lifecycle.
- `bot_commands.py`: register_commands(client) and slash-command synchronization.
- `bot_events.py`: register_events(client, tree) for ready, join, and message events.
- `features/`: registration, giveaways, birthdays, leaderboard, and member linking.
- `database/`, `gwcdbbot.sql`: database access and schema.
- `tests/`: bot and analytics tests.
- `dashboard/`: Insights website and export tools.

## Feature details

Registration collects name, major, optional birthday and phone. Existing registrations
are not overwritten. Members with blocked DMs can enable them and retry `/registration`.
The form does not assign Discord roles.

Automatic birthday greetings are limited to active members and one per year.
February 29 birthdays are celebrated in leap years. `!testbirthday [YYYY-MM-DD]`
requires Manage Server and test mode; it does not change delivery history.

Giveaway durations range from 10 seconds to 30 days (for example, 30s or 2h).
Each active registered member can enter once. A winner is selected randomly;
points do not affect the odds. Creator, prize, entries, deadline, draw time and
winner are saved. Overdue draws finish after restart. Give the bot Read Message
History permission so it can update results and recover announcements.

## Dashboard

GWC Insights uses React/Vinext and Sites hosting with a D1 snapshot store. SQLite
remains the source of truth. The dashboard shows member counts, majors, points,
giveaway history, and event attendance when those records are available.

Keep the hosted dashboard private: its data routes rely on the platform access
controls. Exports exclude birthdays and phone numbers. See
[the sync guide](dashboard/public/sync-guide.txt) for export and upload commands.
The exporter reads SQLite without changing it. The dashboard stays accessible
when the bot is offline, but updates require the sync process to be running.

Website scripts are in `dashboard/package.json`. Use the Sites build/publish
workflow for deployment and `npm run db:generate` after schema changes.

## Team integration

`GWCBot` creates the feature objects, calls `register_commands(self)` once, then
`register_events(self, self.tree)`. Its setup hook initializes the feature tables,
starts background tasks, and synchronizes commands. Its close method stops tasks.

Add teammates' command decorators to the existing tree in `bot_commands.py`;
do not create a second CommandTree or replace setup_hook. Add shared event
behavior inside `bot_events.py`; registering another on_member_join replaces
the existing handler. Registration must continue to use the DM welcome feature.

Set GUILD_ID to register commands for the development server; without it, commands
are global. This branch upserts commands individually so other registered commands
are preserved. After the complete team command set is integrated, the team can
choose bulk tree synchronization in one place.

The team's event/check-in/points command helpers still need integration.
The database package contains the current connector and the recovered original
registration, inspection, and export helpers.

## How the client fits together

`bot.py` calls `main()` in `gwcbot.py`. Main opens the database and creates one
`GWCBot`, a subclass of `discord.Client`, then calls `run(token)`.

That client owns the database connection, command tree, and feature instances.
`register_commands(client)` attaches slash commands to its tree;
`register_events(client, tree)` attaches Discord event callbacks to the same client.
Feature modules receive that client and do not create their own Discord connection.

At login, setup_hook initializes links and persistent welcome buttons, synchronizes
commands, then starts birthday and giveaway tasks. on_ready only logs readiness;
it does not repeat setup after reconnects. close stops the tasks and views.

A join calls on_member_join → welcome.handle_join → public greeting + private DM.
A slash command calls its bot_commands callback → the relevant feature.
Form submissions save through the shared database connection.

When adding features, keep one Client, one CommandTree and one setup_hook. Extend
the existing event handlers rather than registering competing copies. The dashboard
is a separate service and receives exported snapshots; it is not another bot client.

## Recovered original database work

Recovered byte-for-byte from commit `434e13b`:

- `database/gwcbot.sql`: original Members, Events, and Event_Participation schema.
- `database/database_helpers/registration.py`: original registration queries and forms.
- `database/database_helpers/check_database.py`: original member inspection queries.
- `database/database_helpers/export_data.py`: original Excel export and queries (requires openpyxl).
- `database/setup_database.py`: original database creation script.

These files have not been executed or connected to the current bot. Their paths
were organized, but their contents were preserved exactly. The scripts refer to
`gwcbot.db` (and setup to `gwcbot.sql`) relative to the working directory. Do not run
the setup script against an existing database; importing inspection/export scripts
also runs their top-level code.

`database/__init__.py` preserves the current bot's connector, so existing
`from database import connect_database` imports still work. The current bot uses
first_name/last_name and a separate Discord-link table; the original schema uses
full_name and discord_id in Members. Neither schema replaces the other. A deliberate
adapter or migration is still needed before running current features against the
original schema. This recovery does not migrate or modify database records.

## Verification and remaining integration

The automated suite covers the single client/tree, command registration, private
DM registration, random member IDs, giveaways, birthdays, leaderboards, and analytics.
Run `python -m unittest discover -s tests -v` from the repository root.

The analytics exporter accepts both member-name formats. The bot still requires
the newer member schema and refuses the original schema with an explanation;
restoring the original helpers does not automatically integrate them. Original
SQL and helper sources remain unchanged. No live database migration has been run.

Before a full-team demo, integrate the original schema through an adapter and
connect the team's event/check-in/points modules. Test joins, DMs, slash commands,
permissions and timed giveaways in Discord with one running client. Automated
Discord mocks cannot verify live server settings. The website deployment is separate
from a GitHub push and has not been rebuilt or redeployed during this review.
