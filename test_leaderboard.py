import datetime as dt
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo
from gwcbot import GWCBot
from leaderboard import leaderboard_page, leaderboard_embed

class LeaderboardTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.execute('CREATE TABLE Members(member_id INTEGER PRIMARY KEY, first_name, last_name, points_balance INTEGER, member_status)')
        self.db.executemany('INSERT INTO Members VALUES(?,?,?,?,?)', [
            (1,'Avery','Test',150,'active'), (2,'Jordan','Sample',100,'active'),
            (3,'Riley','Demo',100,'active'), (4,'Morgan','Fictional',999,'inactive'),
            (5,'Casey','Example',0,'active')])

    def tearDown(self):
        self.db.close()

    def test_ranks_ties_and_active_filter(self):
        rows, total, pages = leaderboard_page(self.db)
        self.assertEqual([(r['member_id'],r['rank']) for r in rows], [(1,1),(2,2),(3,2),(5,4)])
        self.assertEqual((total,pages),(4,1))
        self.assertIn('150 points',leaderboard_embed(rows,total,pages).description)

    def test_pagination_global_ranks_and_bounds(self):
        self.db.executemany('INSERT INTO Members VALUES(?,?,?,?,?)', [(i,f'Member{i:02}','Test',50,'active') for i in range(6,21)])
        first, total, pages = leaderboard_page(self.db,1)
        second, _, _ = leaderboard_page(self.db,2)
        self.assertEqual((len(first),len(second),total,pages),(10,9,19,2))
        self.assertEqual(second[0]['rank'],4)
        self.assertFalse({r['member_id'] for r in first} & {r['member_id'] for r in second})
        self.assertEqual(second[-1]['rank'],19)
        for page in (0,-1,3):
            with self.assertRaises(ValueError):
                leaderboard_page(self.db,page)

    def test_empty_and_safe_names(self):
        self.db.execute('DELETE FROM Members')
        rows,total,pages=leaderboard_page(self.db)
        self.assertIn('No active members',leaderboard_embed(rows,total,pages).description)
        self.db.execute('INSERT INTO Members VALUES(1,?,?,0,?)',('@everyone\n**name**','Test','active'))
        rows,total,pages=leaderboard_page(self.db)
        embed=leaderboard_embed(rows,total,pages)
        self.assertNotIn('@everyone',embed.description)
        self.assertLess(len(embed.description),4096)

    async def test_command_regular_member_and_no_writes(self):
        bot=GWCBot(self.db,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        channel=SimpleNamespace(send=AsyncMock())
        message=SimpleNamespace(author=SimpleNamespace(bot=False,guild_permissions=SimpleNamespace(manage_guild=False)),guild=object(),content='!leaderboard',channel=channel)
        changes=self.db.total_changes
        await bot.on_message(message)
        self.assertIn('Avery',channel.send.await_args.kwargs['embed'].description)
        self.assertEqual(channel.send.await_args.kwargs['allowed_mentions'].to_dict()['parse'],[])
        message.content='!testleaderboard'
        await bot.on_message(message)
        self.assertEqual(channel.send.await_count,2)
        message.content='!leaderboard 999'
        await bot.on_message(message)
        self.assertIn('Choose a page',channel.send.await_args.args[0])
        message.content='!leaderboard nope'
        await bot.on_message(message)
        self.assertIn('Usage:',channel.send.await_args.args[0])
        message.guild=None
        await bot.on_message(message)
        self.assertEqual(channel.send.await_count,4)
        self.assertEqual(self.db.total_changes,changes)
        await bot.close()
