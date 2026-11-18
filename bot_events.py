"""Discord events shared by the feature modules."""
import logging
from features.member_links import handle_link_command

LOG = logging.getLogger(__name__)


def register_events(client, tree):
    @client.event
    async def on_ready():
        LOG.info('Online as %s. Test mode: %s. Commands: /registration, /giveaway',
                 client.user, client.test_mode)

    @client.event
    async def on_member_join(member):
        await client.welcome.handle_join(member)

    @client.event
    async def on_message(message):
        if message.author.bot or message.guild is None:
            return
        parts = message.content.split()
        if not parts:
            return
        command = parts[0].lower()
        if command == '!testbirthday':
            await client.birthdays.handle_message(message)
        elif command in ('!leaderboard', '!testleaderboard'):
            await client.leaderboard.handle_message(message)
        elif command == '!linkmember':
            await handle_link_command(client, message)
