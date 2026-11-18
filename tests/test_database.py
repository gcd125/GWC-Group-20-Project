import sqlite3
import tempfile
import unittest
from pathlib import Path
from database import connect_database
from dashboard.tools.export_analytics import snapshot

ROOT = Path(__file__).resolve().parents[1]

class DatabaseTests(unittest.TestCase):
    def test_original_schema_is_preserved_and_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'original.db'
            db=sqlite3.connect(path)
            db.executescript((ROOT/'database/gwcbot.sql').read_text())
            db.execute("INSERT INTO Members(member_id,discord_id,full_name) VALUES(1,'123','Original Member')")
            db.commit()
            db.close()
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'schema adapter'):
                connect_database(path)
            exported=snapshot(path)
            self.assertEqual(exported['members'][0]['name'],'Original Member')
            self.assertTrue(exported['members'][0]['linked'])
            self.assertTrue(exported['availability']['events'])
            self.assertEqual(path.read_bytes(),before)

    def test_current_schema_opens_and_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.db'
            with self.assertRaises(sqlite3.OperationalError):
                connect_database(path)
            self.assertFalse(path.exists())
            db=sqlite3.connect(path)
            db.executescript((ROOT/'gwcdbbot.sql').read_text())
            db.close()
            db=connect_database(path)
            self.assertEqual(db.execute('SELECT count(*) FROM Members').fetchone()[0],0)
            db.close()
