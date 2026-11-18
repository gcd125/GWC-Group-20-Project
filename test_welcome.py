import datetime as dt
import asyncio
import sqlite3
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo
from gwcbot import GWCBot
from giveaways import GiveawayStore, EnterGiveawayView
from member_links import initialize_links
from welcome import register_member, RegistrationView, RegistrationPromptView, WelcomeFeature

class WelcomeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('''CREATE TABLE Members(member_id INTEGER PRIMARY KEY, member_role TEXT NOT NULL,
            first_name TEXT NOT NULL,last_name TEXT NOT NULL,member_dob TEXT,major TEXT NOT NULL,
            phone_number TEXT UNIQUE,member_status TEXT,points_balance INTEGER)''')
        initialize_links(self.db)

    def tearDown(self):
        self.db.close()

    def test_registration_link_and_duplicate(self):
        member,created=register_member(self.db,10,20,'Avery','Test','CS','02/29')
        self.assertTrue(created)
        self.assertEqual(self.db.execute('SELECT member_dob FROM Members').fetchone()[0],'02-29')
        self.assertEqual(register_member(self.db,10,20,'Changed','Name','Math'),(member,False))
        self.assertEqual(self.db.execute('SELECT first_name FROM Members').fetchone()[0],'Avery')
        self.assertEqual(self.db.execute('SELECT member_id FROM Member_Discord_Links').fetchone()[0],member)

    def test_random_ids_skip_existing_and_preserve_user_id(self):
        with patch('welcome.secrets.choice', side_effect=lambda available: available[0]):
            first, _ = register_member(self.db,10,20,'A','B','CS')
            second, _ = register_member(self.db,10,21,'C','D','CS')
            repeated, created = register_member(self.db,10,20,'A','B','CS')
        self.assertEqual((first,second,repeated,created),(1,2,1,False))
        self.assertEqual(f'{first:04d}', '0001')

    def test_id_capacity_fails_without_partial_registration(self):
        self.db.executemany("INSERT INTO Members(member_id,member_role,first_name,last_name,major) VALUES (?,'member','A','B','CS')",
                            ((i,) for i in range(1,10000)))
        self.db.commit()
        with self.assertRaisesRegex(ValueError, '9,999'):
            register_member(self.db,10,20,'A','B','CS')
        self.assertEqual(self.db.execute('SELECT count(*) FROM Members').fetchone()[0],9999)
        self.assertEqual(self.db.execute('SELECT count(*) FROM Member_Discord_Links').fetchone()[0],0)

    def test_invalid_and_conflicting_records_rollback(self):
        for birthday in ['02/30','13/01','abc']:
            with self.assertRaises(ValueError): register_member(self.db,1,2,'A','B','CS',birthday)
        register_member(self.db,1,2,'A','B','CS',phone='555-0100')
        with self.assertRaises(ValueError): register_member(self.db,1,3,'C','D','CS',phone='555-0100')
        self.assertEqual(self.db.execute('SELECT count(*) FROM Members').fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM Member_Discord_Links').fetchone()[0],1)

    async def test_command_routing_and_button(self):
        bot=GWCBot(self.db,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        user=NS(id=20,bot=False,send=AsyncMock(return_value=NS(id=600)))
        bot.welcome.initialize_command_history()
        message=NS(id=500,content='!registration',author=user,guild=NS(id=10),channel=NS(send=AsyncMock(return_value=NS(id=600))))
        await asyncio.gather(bot.welcome.handle_message(message), bot.welcome.handle_message(message))
        message.channel.send.assert_not_awaited()
        user.send.assert_awaited_once()
        sent=user.send.await_args.kwargs
        self.assertIn('Your responses are private',sent['embed'].description)
        view=sent['view']
        self.assertTrue(view.is_persistent())
        guild = NS(id=10)
        bot.get_guild = lambda guild_id: guild if guild_id == 10 else None
        interaction=NS(user=user,guild=None,message=NS(id=600),response=NS(send_modal=AsyncMock(),send_message=AsyncMock(),defer=AsyncMock()),followup=NS(send=AsyncMock()))
        # A fresh persistent view resolves the original server after restart.
        restarted_view = RegistrationView(bot.welcome)
        await restarted_view.children[0].callback(interaction)
        restarted_view.stop()
        modal=interaction.response.send_modal.await_args.args[0]
        for field,value in [(modal.first_name,'Avery'),(modal.last_name,'Test'),(modal.major,'CS'),(modal.birthday,dt.datetime.now(bot.timezone).strftime('%m/%d')),(modal.phone,'')]:
            field._value=value
        general = NS(name='general', send=AsyncMock(return_value=NS(id=12345)))
        guild.text_channels = [general]
        with patch.dict('os.environ', {'GENERAL_CHANNEL_ID': ''}):
            await modal.on_submit(interaction)
            await bot.birthdays.handle_registration(
                self.db.execute('SELECT member_id FROM Members').fetchone()[0], guild)
        general.send.assert_awaited_once()
        self.assertIn('Happy Birthday, Avery', general.send.await_args.kwargs['embed'].title)
        self.assertTrue(interaction.followup.send.await_args.kwargs['ephemeral'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM Members').fetchone()[0],1)
        # A normal form submission must immediately qualify for giveaway entry.
        store = GiveawayStore(self.db)
        store.initialize()
        giveaway_id = store.create(10, 30, 99, 'Registration integration test', 60, prize='Shirt')
        store.activate(giveaway_id, 400)
        interaction.guild = guild
        interaction.message = NS(id=400)
        entry_view = EnterGiveawayView(bot.giveaways)
        await entry_view.children[0].callback(interaction)
        self.assertIn('You’re entered', interaction.response.send_message.await_args.args[0])
        saved = self.db.execute('SELECT member_id, discord_id FROM Giveaway_Entries').fetchone()
        registered = self.db.execute('SELECT member_id FROM Members').fetchone()[0]
        self.assertEqual(tuple(saved), (registered, '20'))
        await entry_view.children[0].callback(interaction)
        self.assertIn('already entered', interaction.response.send_message.await_args.args[0])
        self.assertEqual(self.db.execute('SELECT count(*) FROM Giveaway_Entries').fetchone()[0], 1)
        entry_view.stop()
        await view.children[0].callback(interaction)
        self.assertTrue(interaction.response.send_message.await_args.kwargs['ephemeral'])
        message.guild=None
        await bot.on_message(message)
        message.channel.send.assert_not_awaited()
        restarted = WelcomeFeature(bot)
        await restarted.handle_message(NS(id=500,author=user,guild=guild,channel=message.channel))
        user.send.assert_awaited_once()
        user.send.return_value=NS(id=601)
        await restarted.handle_message(NS(id=501,author=user,guild=guild,channel=message.channel))
        self.assertEqual(user.send.await_count,2)
        view.stop()
        await bot.close()

    async def test_blocked_dm_has_no_public_registration_card(self):
        import discord
        bot=GWCBot(self.db,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        bot.welcome.initialize_command_history()
        denied=discord.Forbidden(NS(status=403,reason='Forbidden'), 'Cannot send messages to this user')
        user=NS(id=20,bot=False,send=AsyncMock(side_effect=denied))
        channel=NS(send=AsyncMock())
        message=NS(id=900,author=user,guild=NS(id=10),channel=channel)
        with self.assertLogs('welcome',level='WARNING'):
            await bot.welcome.handle_message(message)
        self.assertIn('Enable direct messages',channel.send.await_args.args[0])
        self.assertNotIn('embed',channel.send.await_args.kwargs)
        self.assertEqual(self.db.execute('SELECT count(*) FROM Registration_DMs').fetchone()[0],0)
        await bot.close()

    def test_existing_welcome_history_migration(self):
        self.db.execute('CREATE TABLE Welcome_Commands(message_id TEXT PRIMARY KEY, response_id TEXT, created_at INTEGER)')
        self.db.execute("INSERT INTO Welcome_Commands VALUES ('old', '123', 1)")
        self.db.commit()
        feature = WelcomeFeature(NS(db=self.db))
        feature.initialize_command_history()
        feature.initialize_command_history()
        row = self.db.execute('SELECT response_id, recipient_id FROM Welcome_Commands').fetchone()
        self.assertEqual(tuple(row), ('123', None))

    async def test_join_welcome_and_rejoin(self):
        bot = GWCBot(self.db,None,ZoneInfo('America/New_York'),dt.time(9),test_mode=True)
        self.assertTrue(bot.intents.members)
        bot.welcome.initialize_command_history()
        channel = NS(name='welcome',send=AsyncMock(return_value=NS(id=600)))
        guild = NS(id=10,text_channels=[channel],get_channel=lambda channel_id: channel if channel_id==30 else None)
        member = NS(id=20,bot=False,guild=guild,send=AsyncMock(side_effect=[NS(id=700+i) for i in range(10)]),joined_at=dt.datetime(2026,11,17,tzinfo=dt.timezone.utc))
        from unittest.mock import patch
        with patch.dict('os.environ',{'WELCOME_CHANNEL_ID':''}):
            await asyncio.gather(bot.on_member_join(member),bot.on_member_join(member))
            channel.send.assert_awaited_once()
            member.send.assert_awaited_once()
            self.assertNotIn("view", channel.send.await_args.kwargs)
            self.assertIn('<@20>',channel.send.await_args.kwargs['embed'].description)
            member.joined_at += dt.timedelta(days=1)
            await bot.on_member_join(member)
            self.assertEqual(channel.send.await_count,2)
            member.bot=True
            await bot.on_member_join(member)
            self.assertEqual(channel.send.await_count,2)
            member.bot=False
            guild.text_channels=[]
            with self.assertLogs('welcome',level='ERROR'):
                await bot.on_member_join(member)
        member.joined_at += dt.timedelta(days=1)
        with patch.dict('os.environ',{'WELCOME_CHANNEL_ID':'30'}):
            await bot.on_member_join(member)
            self.assertEqual(channel.send.await_count,3)
        await bot.close()
