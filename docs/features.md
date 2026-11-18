# Bot features

## Registration

Joining sends a public greeting without buttons to #welcome and a registration
card by DM. `/registration` resends the DM. Members with blocked DMs need to enable
messages from server members and retry.

The form collects name, major, optional birthday and phone. New members receive a
random unused ID from 0001–9999, zero points, and a Discord link for giveaway entry.
Existing registrations are not overwritten. No Discord roles are assigned.
Organizers can use `!linkmember <ID> @member` for an existing unlinked record.

## Birthdays

New registrations with today's birthday receive a greeting in #general. Production
also checks each minute after BIRTHDAY_TIME (09:00, America/New_York by default).
Test mode disables scheduled greetings, but registration greetings still send.
Active members receive at most one automatic greeting each year. February 29 is
celebrated only in leap years. Pending deliveries need checking before a manual retry.

`!testbirthday [YYYY-MM-DD]` requires test mode and Manage Server permission.
It posts previews in the command channel without changing delivery history.

## Giveaways

Use `/giveaway`, click New Giveaway, and enter a name, prize, and duration (30s,
10m, 2h). Durations range from 10 seconds to 30 days. Creation is open to members
unless GIVEAWAY_HOST_ROLE_ID is set; then that role or Manage Server is required.

Members with active linked registrations can click Enter Giveaway once. One
eligible entrant is chosen randomly; points do not affect the odds. Results update
the original post and a separate message congratulates the winner with their prize.

Creator, entries, prize, deadline, draw time, winner and delivery state are saved.
Overdue giveaways finish when the bot restarts. Read Message History permission is
needed to update messages and recover announcements.

## Data and operation

Test mode uses gwc_test.db; production uses GWC_DATABASE_PATH. The base schema is
gwcdbbot.sql. Link, delivery and giveaway tables are created at startup.
Never commit real databases. Run only one bot instance per Discord application.
The bot needs an awake host; the hosted dashboard is a separate service.
