import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from features.giveaways import GiveawayStore, GiveawayFeature, EnterGiveawayView, NewGiveawayView, parse_duration
from features.member_links import initialize_links, link_member

async def empty_history(**kwargs):
    for message in []:
        yield message

class GiveawayTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'test.db'
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("CREATE TABLE Members(member_id INTEGER PRIMARY KEY, member_status); INSERT INTO Members VALUES(1,'active'),(2,'active'),(3,'inactive');")
        initialize_links(self.db)
        link_member(self.db,10,100,1)
        link_member(self.db,10,200,2)
        self.store = GiveawayStore(self.db)
        self.store.initialize()

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def create(self, now=1000):
        gid=self.store.create(10,20,100,'Fall Shirt Giveaway',30,now=now)
        self.store.activate(gid,300+gid)
        return gid

    def test_history_survives_restart_and_retry(self):
        gid = self.store.create(10,20,100,'Fall Giveaway',30,now=1000,prize='GWC shirt')
        self.store.activate(gid,555)
        self.store.enter(555,10,200,1001)
        row = self.store.finish(gid,1045)
        self.assertEqual((row['host_id'],row['prize'],row['created_at'],row['ends_at'],
                          row['finished_at'],row['winner_id'],row['winner_member_id']),
                         ('100','GWC shirt',1000,1030,1045,'200',2))
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        recovered = GiveawayStore(self.db)
        recovered.initialize()
        self.assertEqual(dict(recovered.finish(gid,1100)),dict(row))
        empty = recovered.create(10,20,100,'Empty',30,now=1000,prize='Sticker')
        recovered.activate(empty,556)
        result = recovered.finish(empty,1030)
        self.assertEqual(result['finished_at'],1030)
        self.assertIsNone(result['winner_member_id'])

    def test_existing_database_migration_preserves_history(self):
        with sqlite3.connect(':memory:') as db:
            db.row_factory = sqlite3.Row
            db.executescript("""
                CREATE TABLE Giveaways (
                    id INTEGER PRIMARY KEY, guild_id TEXT, channel_id TEXT,
                    message_id TEXT, host_id TEXT, name TEXT, ends_at INTEGER,
                    status TEXT, winner_id TEXT, eligible_count INTEGER, published INTEGER);
                INSERT INTO Giveaways VALUES(1,'10','20','300','100','Old giveaway',1000,
                    'finished','200',1,1);
            """)
            store = GiveawayStore(db)
            store.initialize()
            store.initialize()
            row = store.get(1)
            self.assertEqual((row['name'],row['winner_id'],row['published']),('Old giveaway','200',1))
            self.assertIsNone(row['created_at'])
            self.assertIsNone(row['finished_at'])
            self.assertIsNone(row['prize'])

    def test_duration(self):
        for text, seconds in [('30s',30),('10m',600),('2h',7200),('7d',604800),(' 1H ',3600)]:
            self.assertEqual(parse_duration(text),seconds)
        for value in ['0m','9s','31d','-1m','tomorrow','1.5h','999999999999d']:
            with self.assertRaises(ValueError): parse_duration(value)

    def test_opt_in_duplicate_deadline_and_guild(self):
        gid=self.create()
        self.assertTrue(self.store.enter(300+gid,10,100,1001))
        self.assertFalse(self.store.enter(300+gid,10,100,1002))
        for guild,user,now in [(10,999,1002),(11,100,1002),(10,200,1030)]:
            with self.assertRaises(ValueError): self.store.enter(300+gid,guild,user,now)
        row=self.store.finish(gid,1030)
        self.assertEqual(row['winner_id'],'100')
        self.assertEqual(row['eligible_count'],1) # registered user 200 never entered
        self.assertEqual(self.store.finish(gid,1040)['winner_id'],'100')

    def test_restart_and_ineligible_entries(self):
        gid=self.create()
        self.store.enter(300+gid,10,100,1001)
        self.store.enter(300+gid,10,200,1001)
        with self.db: self.db.execute("UPDATE Members SET member_status='inactive' WHERE member_id=1")
        self.db.close()
        self.db=sqlite3.connect(self.path)
        self.db.row_factory=sqlite3.Row
        recovered=GiveawayStore(self.db)
        self.assertEqual(len(recovered.pending(1031)),1)
        row=recovered.finish(gid,1031)
        self.assertEqual((row['winner_id'],row['eligible_count']),('200',1))
        def no_redraw(_): raise AssertionError('Must not draw again')
        self.assertEqual(recovered.finish(gid,1040,chooser=no_redraw)['winner_id'],'200')

    def test_empty_and_early_draw(self):
        gid=self.create()
        self.assertEqual(self.store.finish(gid,1001)['status'],'active')
        row=self.store.finish(gid,1030)
        self.assertIsNone(row['winner_id'])
        self.assertEqual(row['eligible_count'],0)

    def test_links_do_not_allow_impersonation(self):
        for user,member in [(999,1),(100,2),(333,3),(333,999)]:
            with self.assertRaises(ValueError): link_member(self.db,10,user,member)
        link_member(self.db,10,100,1) # idempotent

    async def test_result_retry_uses_saved_winner(self):
        gid=self.create(now=int(time.time())-100)
        # Enter before deadline using the clock under test.
        self.store.enter(300+gid,10,100,int(time.time())-90)
        message=NS(edit=AsyncMock(side_effect=[RuntimeError('network'),None]))
        channel=NS(fetch_message=AsyncMock(return_value=message), history=empty_history, send=AsyncMock(return_value=NS(id=888)))
        bot=NS(db=self.db,user=None,get_channel=lambda _:channel)
        feature=GiveawayFeature(bot)
        with self.assertLogs('features.giveaways',level='ERROR'): await feature.settle_due()
        self.assertEqual(self.store.get(gid)['published'],0)
        self.assertEqual(self.store.get(gid)['winner_id'],'100')
        await feature.settle_due()
        self.assertEqual(self.store.get(gid)['published'],1)
        self.assertIsNone(message.edit.await_args.kwargs['view'])
        await feature.settle_due()
        self.assertEqual(message.edit.await_count,2)
        self.assertEqual(channel.send.await_count,1)
        self.assertEqual(self.store.get(gid)['announcement_message_id'],'888')
        self.assertIn('Fall Shirt Giveaway',channel.send.await_args.kwargs['embed'].description)

    async def test_announcement_recovers_ambiguous_send(self):
        gid=self.create(now=int(time.time())-100)
        self.store.enter(300+gid,10,100,int(time.time())-90)
        posted=[]
        async def history(**kwargs):
            for message in posted:
                yield message
        async def send(**kwargs):
            posted.append(NS(id=889,author=NS(id=42),embeds=[kwargs['embed']]))
            raise RuntimeError('Response lost after Discord accepted message')
        message=NS(edit=AsyncMock())
        channel=NS(fetch_message=AsyncMock(return_value=message),history=history,send=AsyncMock(side_effect=send))
        bot=NS(db=self.db,user=NS(id=42,display_avatar=NS(url='https://example.com/avatar.png')),get_channel=lambda _:channel)
        feature=GiveawayFeature(bot)
        with self.assertLogs('features.giveaways',level='ERROR'):
            await feature.settle_due()
        winner=self.store.get(gid)['winner_id']
        await GiveawayFeature(bot).settle_due()
        self.assertEqual(channel.send.await_count,1)
        self.assertEqual(message.edit.await_count,1)
        self.assertEqual(self.store.get(gid)['announcement_message_id'],'889')
        self.assertEqual(self.store.get(gid)['winner_id'],winner)
        self.assertEqual(len(self.store.pending()),0)

    async def test_empty_giveaway_does_not_announce_winner(self):
        gid=self.create(now=int(time.time())-100)
        channel=NS(fetch_message=AsyncMock(return_value=NS(edit=AsyncMock())),send=AsyncMock())
        feature=GiveawayFeature(NS(db=self.db,user=None,get_channel=lambda _:channel))
        await feature.settle_due()
        channel.send.assert_not_awaited()
        self.assertEqual(self.store.get(gid)['announced'],1)

    async def test_buttons_and_modal_validation(self):
        bot=NS(db=self.db,user=None)
        feature=GiveawayFeature(bot)
        user=NS(id=100,bot=False,guild_permissions=NS(manage_guild=False),roles=[])
        interaction=NS(user=user,guild=NS(id=10),channel=NS(id=20),response=NS(send_message=AsyncMock(),send_modal=AsyncMock(),defer=AsyncMock()))
        new=NewGiveawayView(feature)
        enter=EnterGiveawayView(feature)
        self.assertTrue(new.is_persistent())
        self.assertTrue(enter.is_persistent())
        await new.children[0].callback(interaction)
        self.assertEqual(interaction.response.send_modal.await_count,1)
        await feature.create_from_modal(interaction,'Fall Shirt','nonsense')
        self.assertEqual(interaction.response.defer.await_count,0)
        feature.host_role_id=999
        await new.children[0].callback(interaction)
        self.assertIn('permission',interaction.response.send_message.await_args.args[0])
        feature.host_role_id=None
        posted=NS(id=777,jump_url='https://discord.com/channels/10/20/777')
        interaction.channel.send=AsyncMock(return_value=posted)
        interaction.followup=NS(send=AsyncMock())
        await feature.create_from_modal(interaction,'Fall Shirt Giveaway','30s','One fall shirt')
        saved = self.db.execute('SELECT * FROM Giveaways').fetchone()
        self.assertEqual(saved['prize'],'One fall shirt')
        self.assertIsNotNone(saved['created_at'])
        self.assertEqual(interaction.channel.send.await_count,1)
        interaction.message=NS(id=777)
        await enter.children[0].callback(interaction)
        self.assertTrue(interaction.response.send_message.await_args.kwargs['ephemeral'])
        self.assertIn('entered',interaction.response.send_message.await_args.args[0])
        new.stop(); enter.stop()
