import datetime as dt
import sqlite3
import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace
from features.birthdays import birthday_matches, send_birthdays, birthday_embed


class BirthdaysTest(unittest.IsolatedAsyncioTestCase):
    def test_embed(self):
        embed = birthday_embed({'first_name': 'Avery'}, thumbnail_url='https://example.com/logo.png')
        self.assertIn('Avery', embed.title)
        self.assertEqual(embed.colour.value, 0x82A7DB)
        self.assertEqual(embed.thumbnail.url, 'https://example.com/logo.png')
        self.assertNotIn('Birthday test', embed.footer.text)

    def test_dates(self):
        today = dt.date(2026, 11, 1)
        for value in ['2000-11-01', '11-01']:
            self.assertTrue(birthday_matches(value, today))
        for value in [None, '', 'invalid', '2000-11-02', '2026-02-30']:
            self.assertFalse(birthday_matches(value, today))
        self.assertTrue(birthday_matches('02-29', dt.date(2028, 2, 29)))
        self.assertFalse(birthday_matches('02-29', dt.date(2027, 2, 28)))

    async def test_delivery_and_duplicate_prevention(self):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.executescript('''CREATE TABLE Members(member_id, first_name, member_dob, member_status);
            INSERT INTO Members VALUES(1, 'Ada', '11-01', 'active'),(2, 'Grace', '11-01', 'inactive'),(3, 'Sam', NULL, 'active');
            CREATE TABLE Birthday_Greetings(member_id, birthday_year, status, message_id, PRIMARY KEY(member_id,birthday_year));''')
        channel = SimpleNamespace(send=AsyncMock(return_value=SimpleNamespace(id=123)))
        await send_birthdays(db, channel, dt.date(2026, 11, 1))
        await send_birthdays(db, channel, dt.date(2026, 11, 1))
        self.assertEqual(channel.send.await_count, 1)
        self.assertIn('Ada', channel.send.await_args.kwargs['embed'].title)
        self.assertNotIn('Birthday test', channel.send.await_args.kwargs['embed'].footer.text)
        self.assertEqual(db.execute('SELECT status FROM Birthday_Greetings').fetchone()[0], 'sent')
        await send_birthdays(db, channel, dt.date(2027, 11, 1))
        self.assertEqual(channel.send.await_count, 2)
        channel.send.side_effect = TimeoutError('uncertain delivery')
        with self.assertLogs('features.birthdays', level='ERROR'):
            await send_birthdays(db, channel, dt.date(2028, 11, 1))
        await send_birthdays(db, channel, dt.date(2028, 11, 1))
        self.assertEqual(channel.send.await_count, 3)
        self.assertEqual(db.execute('SELECT status FROM Birthday_Greetings WHERE birthday_year=2028').fetchone()[0], 'pending')
        db.close()


if __name__ == '__main__':
    unittest.main()
