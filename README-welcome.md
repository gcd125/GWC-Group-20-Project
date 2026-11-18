# Welcome and registration

Restart the bot and send /registration in a server text channel. It posts the blue
welcome embed and a persistent Start Registration button. New human members automatically receive this card in the server text channel
named welcome. Set WELCOME_CHANNEL_ID to choose a specific channel. This restores the screenshot layout; the original welcome
implementation was not present in the available project files.

The private registration form collects first name, last name, major, optional
birthday (MM/DD), and optional phone. It creates an active member with zero points
and member role, and saves the Discord link in the same database transaction.
It never grants Discord roles. Existing linked records are not overwritten.
Unlinked existing members should ask an organizer to link their registration
instead of creating another one. Names alone are not used for identity matching.

With the current test launcher, submissions go into gwc_test.db. Use fictional
form details while testing. In live mode they go into GWC_DATABASE_PATH. Club
organizers with database access can view records; responses are not posted to
other server members. Do not publish the database or commit it to a repository.

Old welcome buttons from a different implementation may not work: use the new
post created with /registration. Enable Server Members Intent in Discord Developer Portal → Bot → Privileged Gateway Intents before restarting. Message Content Intent is also required for the backup command. Automatic joins run in test mode too; submissions use gwc_test.db. The bot needs View Channel, Send Messages, and Embed Links in the welcome channel. Existing members are not greeted on startup. Test with a new join while the bot is online. Only one bot instance should run.


## Public welcome and private registration
Joining sends a public blue welcome embed with no buttons, plus a separate DM
containing the registration card and Start Registration button.
/registration sends only the DM, allowing a test without leaving the server.
DM message IDs map to the recipient and original server in Registration_DMs;
this preserves giveaway linking and birthday delivery when the form is submitted
from a DM, including after a restart. Existing registrations are not overwritten.
Blocked DMs never fall back to a public registration card. The backup command
explains how to enable DMs and retry. Old public cards are not removed automatically.
