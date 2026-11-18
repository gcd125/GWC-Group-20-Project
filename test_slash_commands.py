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
        await command.callback(i)
        self.assertTrue(i.response.defer.await_args.kwargs['ephemeral'])
        self.assertTrue(i.followup.send.await_args.kwargs['ephemeral'])
        bot.welcome.handle_message=AsyncMock()
        await bot.on_message(NS(guild=i.guild,author=i.user,content='!registration'))
        bot.welcome.handle_message.assert_not_awaited()
        await bot.close()

    async def test_giveaway_rejects_dm_and_privately_opens_host_controls(self):
        bot=GWCBot(None,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        i=NS(guild=None,user=NS(bot=False),response=NS(send_message=AsyncMock()))
        await bot.tree.get_command('giveaway').callback(i)
        self.assertIn('permission',i.response.send_message.await_args.args[0])
        i.guild=NS(id=2)
        bot.giveaways.can_host=lambda user: True
        await bot.tree.get_command('giveaway').callback(i)
        sent=i.response.send_message.await_args.kwargs
        self.assertTrue(sent['ephemeral'])
        self.assertIn('Giveaways',sent['embed'].title)
        sent['view'].stop()
        await bot.close()


class SyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_uses_only_selected_scope(self):
        from bot_commands import sync_commands
        from unittest.mock import patch
        bot=GWCBot(None,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        bot.http.upsert_guild_command=AsyncMock()
        bot.http.upsert_global_command=AsyncMock()
        with patch.dict('os.environ', {'GUILD_ID': '123'}):
            await sync_commands(bot,bot.tree)
        self.assertEqual(bot.http.upsert_guild_command.await_count,2)
        bot.http.upsert_global_command.assert_not_awaited()
        with patch.dict('os.environ', {'GUILD_ID': ''}):
            await sync_commands(bot,bot.tree)
        self.assertEqual(bot.http.upsert_global_command.await_count,2)
        await bot.close()


class ClientStructureTests(unittest.IsolatedAsyncioTestCase):
    async def test_features_share_one_client_and_tree(self):
        import discord
        from bot_commands import register_commands
        bot=GWCBot(None,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        self.assertIsInstance(bot,discord.Client)
        tree=bot.tree
        self.assertIs(register_commands(bot),tree)
        self.assertEqual(len(tree.get_commands()),2)
        for feature in (bot.welcome,bot.birthdays,bot.giveaways,bot.leaderboard):
            self.assertIs(feature.bot,bot)
        await bot.close()

    async def test_failed_sync_does_not_start_background_tasks(self):
        import sqlite3
        from unittest.mock import patch, Mock
        db=sqlite3.connect(':memory:')
        bot=GWCBot(db,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        bot.birthdays.start=Mock()
        bot.giveaways.start=Mock()
        with patch('gwcbot.sync_commands',new=AsyncMock(side_effect=RuntimeError('sync failed'))):
            with self.assertRaises(RuntimeError):
                await bot.setup_hook()
        bot.birthdays.start.assert_not_called()
        bot.giveaways.start.assert_not_called()
        await bot.close()
        db.close()
