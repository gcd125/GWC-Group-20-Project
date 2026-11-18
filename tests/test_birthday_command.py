import datetime as dt
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo
from gwcbot import GWCBot

class CommandTest(unittest.IsolatedAsyncioTestCase):
    async def test_command(self):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.executescript("CREATE TABLE Members(member_id,first_name,member_dob,member_status); INSERT INTO Members VALUES (1,'Avery','11-03','active');")
        bot = GWCBot(db, None, ZoneInfo('America/New_York'), dt.time(9), test_mode=True)
        message = SimpleNamespace(author=SimpleNamespace(bot=False, guild_permissions=SimpleNamespace(manage_guild=True)), guild=object(), content='!testbirthday 2026-11-03', channel=SimpleNamespace(send=AsyncMock()))
        bot.http.upsert_global_command = AsyncMock()
        await bot.setup_hook()
        self.assertFalse(bot.birthdays.check_birthdays.is_running())
        for _ in range(2):
            await bot.on_message(message)
        self.assertEqual(message.channel.send.await_count,2)
        self.assertIn('Avery', message.channel.send.await_args.kwargs['embed'].title)
        self.assertNotIn('Birthday test', message.channel.send.await_args.kwargs['embed'].footer.text)
        self.assertEqual(db.execute("SELECT count(*) FROM Birthday_Greetings").fetchone()[0],0)
        message.content='!testbirthday bad-date'
        await bot.on_message(message)
        self.assertIn('Usage:',message.channel.send.await_args.args[0])
        message.content='!testbirthday 2026-11-05'
        await bot.on_message(message)
        self.assertIn('No active',message.channel.send.await_args.args[0])
        message.author.guild_permissions.manage_guild=False
        await bot.on_message(message)
        self.assertIn('Manage Server',message.channel.send.await_args.args[0])
        message.author.guild_permissions.manage_guild=True
        bot.test_mode=False
        await bot.on_message(message)
        self.assertIn('--test-mode',message.channel.send.await_args.args[0])
        await bot.close()
        db.close()
