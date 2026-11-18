import sqlite3
import tempfile
import unittest
from pathlib import Path
from export_analytics import snapshot

class ExportTests(unittest.TestCase):
    def test_missing_tables_and_no_private_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'gwc_test.db'
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE Members(member_id INTEGER,first_name,last_name,major,member_status,points_balance,phone_number,member_dob)')
                db.execute("INSERT INTO Members VALUES(1,'A','B','CS','active',0,'private-phone','private-dob')")
            result=snapshot(p)
            self.assertFalse(result['availability']['events'])
            self.assertFalse(result['availability']['attendance'])
            self.assertTrue(result['testData'])
            self.assertNotIn('private-phone',str(result))
            self.assertNotIn('private-dob',str(result))
            self.assertEqual(result['members'][0]['status'],'active')
            with sqlite3.connect(p) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM sqlite_master WHERE type="table"').fetchone()[0],1)

    def test_attendance_deduplicates_per_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'club.db'
            with sqlite3.connect(p) as db:
                db.executescript('''CREATE TABLE Members(member_id INTEGER,first_name,last_name);
                    INSERT INTO Members VALUES(1,'A','B');
                    CREATE TABLE Events(event_id INTEGER,event_name,event_organizer,event_points);
                    INSERT INTO Events VALUES(10,'Workshop',1,5),(20,'Social',1,0);
                    CREATE TABLE Event_Participation(member_id,event_id,member_attendance);
                    INSERT INTO Event_Participation VALUES(1,10,'present'),(1,10,'present'),(2,10,'not present'),(1,20,'present');''')
            result=snapshot(p)
            self.assertEqual(result['events'][0]['registered'],2)
            self.assertEqual(result['events'][0]['attended'],1)
            self.assertEqual(result['events'][1]['attended'],1)
            self.assertFalse(result['testData'])

if __name__=='__main__':unittest.main()
