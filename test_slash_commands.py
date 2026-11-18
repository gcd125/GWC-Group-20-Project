import datetime as dt
import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace as NS
from zoneinfo import ZoneInfo
from gwcbot import GWCBot

class SlashTests(unittest.IsolatedAsyncioTestCase):
    async def test_registration_is_private_and_old_prefix_is_inactive(self):
        bot=GWCBot(None,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        bot.welcome.send_registration_dm=AsyncMock(return_value=True)
        i=NS(id=1,guild=NS(id=2),user=NS(id=3,bot=False),response=NS(defer=AsyncMock()),followup=NS(send=AsyncMock()))
        command=bot.tree.get_command('registration')
        self.assertTrue(command.guild_only)
        self.assertIs(command.binding, bot)
        await command.callback(bot, i)
        self.assertTrue(i.response.defer.await_args.kwargs['ephemeral'])
        self.assertTrue(i.followup.send.await_args.kwargs['ephemeral'])
        bot.welcome.handle_message=AsyncMock()
        await bot.on_message(NS(guild=i.guild,author=i.user,content='!registration'))
        bot.welcome.handle_message.assert_not_awaited()
        await bot.close()

    async def test_giveaway_rejects_dm_and_privately_opens_host_controls(self):
        bot=GWCBot(None,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        i=NS(guild=None,user=NS(bot=False),response=NS(send_message=AsyncMock()))
        await bot.tree.get_command('giveaway').callback(bot, i)
        self.assertIn('permission',i.response.send_message.await_args.args[0])
        i.guild=NS(id=2)
        bot.giveaways.can_host=lambda user: True
        await bot.tree.get_command('giveaway').callback(bot, i)
        sent=i.response.send_message.await_args.kwargs
        self.assertTrue(sent['ephemeral'])
        self.assertIn('Giveaways',sent['embed'].title)
        sent['view'].stop()
        await bot.close()
