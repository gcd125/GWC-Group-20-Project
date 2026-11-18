# GWC birthday greetings

Uses an existing SQLite registration database with the Members table from gwcdbbot.sql. The SQL file is only a schema, not a populated database, and its unfinished Points_Management declaration means it cannot currently be executed as a complete initialization script. This feature does not change that schema file or import registrations.

Set environment variables before starting (no secrets belong in the source):

- GWC_DATABASE_PATH: absolute path to the populated SQLite registration database.
- DISCORD_TOKEN: your Discord bot token.
- GENERAL_CHANNEL_ID: numeric ID of your server's general text channel.
- BIRTHDAY_TIMEZONE: defaults to America/New_York.
- BIRTHDAY_TIME: local 24-hour time, defaults to 09:00.

Use Python 3.10+ with discord.py 2.x (existing virtual environment has 2.7.1).

Run `.venv/bin/python gwcbot.py --preview 2026-11-01` to print a date's messages without sending or writing to the database. Run `.venv/bin/python gwcbot.py` to start the bot. The bot needs View Channel and Send Messages permissions in the chosen channel. Enable Message Content Intent in the Discord Developer Portal for the !testbirthday command.

Birthdays accept YYYY-MM-DD or MM-DD. Missing/invalid birthdays are skipped. Only active members receive greetings. February 29 birthdays are celebrated on February 29 in leap years. Messages use first names because the current schema has no Discord ID field; they do not mention users, roles, or everyone, and never include ages.

The bot checks every minute after the configured time, catching up on the same day if restarted late. It does not send greetings missed on previous days. Keep the process running on an always-on host; a sleeping/offline laptop cannot send messages. Use one bot instance and a local database on that host, not multiple running copies of a OneDrive-synced database.

Birthday_Greetings stores one record per member and year. A pending claim is committed before sending to prevent duplicates after a crash or ambiguous network failure. Such failures may leave a greeting unsent: inspect the channel and pending row before manually reconciling it. Mark a confirmed delivery sent, or delete only the matching pending row if confirmed not delivered, allowing a same-day retry. Do not clear all delivery history.

Tests: `.venv/bin/python -m unittest -v test_birthdays.py` (mock Discord only).

Discord task lifecycle reference: https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html


## Try it in Discord

In the Discord Developer Portal, open your application → Bot → Privileged Gateway Intents and enable Message Content Intent. The bot needs View Channel and Send Messages in the test channel; your account needs Manage Server permission.

Start from Terminal:

```sh
cd "$HOME/OneDrive/GWC Project"
.venv/bin/python gwcbot.py --test-mode
```

If DISCORD_TOKEN is not already set, the program asks for the token with hidden input. Test mode uses only the fictional gwc_test.db next to the script, used for fictional data only; giveaway entries and member links can be saved. It does not require GENERAL_CHANNEL_ID and disables scheduled birthday posts.

In Discord, type `!testbirthday 2026-11-03` for Avery and Jordan, or `!testbirthday 2026-11-04` for Riley. `!testbirthday` uses today's Eastern date. Each greeting uses the same clean embed as automatic greetings and appears in the channel where you typed the command. You can repeat the command; tests do not claim annual greetings. Press Ctrl+C in Terminal to stop.

Intent setup reference: https://discordpy.readthedocs.io/en/stable/intents.html


Birthday greetings now use blue Discord embeds, with the bot avatar as the thumbnail. Set BIRTHDAY_IMAGE_URL to an HTTPS image URL to use custom club artwork. The bot also needs Embed Links permission in the target channel. Neither test nor scheduled greetings display test labels or dates in the footer. Restart the running bot after updates.
