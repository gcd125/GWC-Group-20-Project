# Giveaways

`giveaways.py` owns the creation form, persistent buttons, stored entries, draw, and deadline scheduler. `member_links.py` separately handles verified Discord-to-registration links. `gwcbot.py` routes commands and starts/stops the features.

## Try a 30-second giveaway

1. Restart the bot with the existing Desktop launcher (`gwcbot.py --test-mode`).
2. A server manager sends `!linkmember 9001 @yourself`, replacing @yourself with an actual Discord mention. This connects the real Discord account to fictional Avery's registration. A second tester can be linked to registration 9002. Existing links are not overwritten. This step is only needed once per account.
3. Send `/giveaway` in the desired server text channel.
4. Click **New Giveaway**, enter **Fall Shirt Giveaway**, and enter **30s** as the duration.
5. Click **Enter Giveaway** on the new post. Confirmation is private. Other eligible registered members can click too.
6. After 30 seconds (plus up to the 5-second scheduler interval), the original post updates to show the winner and removes its entry button. No test labels are displayed.

All users may currently create giveaways, as requested. Set `GIVEAWAY_HOST_ROLE_ID` to a Discord role ID and restart to restrict creation to that role or members with Manage Server. The gate applies to the command, button, and form submission. Registration linking always requires Manage Server permission; users cannot claim someone else's registration.

Durations accept whole numbers followed by s, m, h, or d: 30s, 10m, 2h, 7d. Limits: 10 seconds to 30 days. Names: 1–100 characters. One winner is selected with Python's secrets.choice, equally among eligible entrants. Points do not affect the odds. Only users who click Enter Giveaway and have a linked active registration can enter; members who become inactive before the draw are excluded. One entry per member/account/giveaway. The database is the membership authority; leaving Discord alone does not change member_status.

## Persistence and operation

Test mode now opens only the fictional gwc_test.db for writes, allowing saved giveaway entries, results, and member links. It still disables automatic birthday posting. Live mode uses GWC_DATABASE_PATH. Do not use the same database for test and live deployments. New tables are created on bot startup without altering Members or existing point balances.

Keep the bot process running. If it is offline at the deadline, entries are rejected after the stored deadline and the draw/result runs when the bot reconnects. Persistent buttons remain usable after restarts. A result is stored before publishing; publication retries edit the same message with the same winner. Run one bot process per database. The active database should be on a local disk, not concurrently edited/synced across multiple running machines.

The bot needs View Channel, Send Messages, Embed Links, and Read Message History (to retrieve/update the original giveaway message). Message Content Intent is needed for ! commands. Deleting the original message or removing channel permissions prevents result publication; the result stays saved and the bot logs/retries. If initial posting fails or is ambiguous, a draft can remain: inspect the log and channel before creating another giveaway. Drafts never admit entries or draw winners. The separate congratulations post mentions and pings only the winner; the original result card does not ping.

Tables: Giveaways, Giveaway_Entries, Member_Discord_Links. Future registration should populate the verified link at registration time instead of needing the manual !linkmember command.

Run tests:

```sh
.venv/bin/python -m unittest -v test_giveaways.py test_birthdays.py test_birthday_command.py test_leaderboard.py
```

Discord persistent UI reference: https://discordpy.readthedocs.io/en/stable/interactions/api.html

## Permanent giveaway history

The New Giveaway form includes a required Prize field, displayed in the embed.
Giveaways stores the title (name), prize, creator Discord ID (host_id), created_at,
scheduled deadline (ends_at), actual draw time (finished_at), winner Discord ID
(winner_id), winner registration ID (winner_member_id), eligible_count, status,
and server/channel/message IDs. Giveaway_Entries retains entrants and their
registration IDs. Timestamps are Unix seconds (UTC). A delayed draw records its
actual completion time separately from the original deadline. Empty draws have
no winner but retain their completion time and zero eligible entries. Retries do
not change the saved result or completion time.

Existing databases migrate automatically on restart without deleting records.
Previously unrecorded fields on older giveaways stay NULL (unknown).
In test mode this history is in gwc_test.db; live mode uses GWC_DATABASE_PATH.

Example read-only history query (SQLite):

```sql
SELECT id, name, prize, host_id,
       datetime(created_at, 'unixepoch') AS created_utc,
       datetime(ends_at, 'unixepoch') AS deadline_utc,
       datetime(finished_at, 'unixepoch') AS completed_utc,
       winner_id, winner_member_id, eligible_count, status
FROM Giveaways ORDER BY id DESC;
```

## Winner announcement

After updating the original result card, the bot sends a new blue congratulations
embed in the same channel naming the winner and prize. No congratulations post is
sent for an empty draw. The announcement message ID and completion flag are saved
in Giveaways. On retries, the bot checks its own message history for the giveaway
marker before sending again, recovering sends accepted before a lost response or
restart. Read Message History is required. Keep one bot instance per database.
Previously published results are marked handled during migration and are not
announced retroactively. The original post still removes its entry button.
