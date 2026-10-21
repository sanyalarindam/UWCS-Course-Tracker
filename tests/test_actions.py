import datetime as dt
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import app
from tracker.store import Store

DATA = Path(__file__).resolve().parents[1] / '.local-data' / 'tests'
DATA.mkdir(parents=True, exist_ok=True)

def course():
    return {'id':'CSE312-2026-Autumn','code':'CSE312','quarter':'Autumn','year':2026,'url':'https://courses.cs.washington.edu/courses/cse312/26au/', 'notes':'Keep notes', 'events':[{'id':'exam','title':'Midterm','kind':'exam','date':'2026-11-04','time':None}], 'materials':[]}

class UndoTests(unittest.TestCase):
    def test_remove_restores_notes_and_completion_and_survives_restart(self):
        with tempfile.TemporaryDirectory(dir=DATA) as directory:
            store = Store(directory)
            c = course(); store.save_course(c); store.completion('exam', True)
            store.mutate_with_undo('delete', {'id':c['id']})
            self.assertEqual(store.courses(), [])
            reopened = Store(directory); reopened.undo()
            self.assertEqual(reopened.courses(), [c])
            self.assertTrue(reopened.completions()['exam'])
            self.assertIsNone(reopened.undo_status())

    def test_completion_and_planner_undo_are_ordered(self):
        with tempfile.TemporaryDirectory(dir=DATA) as directory:
            store = Store(directory)
            store.mutate_with_undo('completion', {'id':'exam','done':True})
            store.mutate_with_undo('planner', {'profile':{'completed':[]},'plan':[{'code':'CSE312'}]})
            store.undo()
            self.assertIsNone(store.get('planner_profile'))
            self.assertTrue(store.completions()['exam'])
            store.undo()
            self.assertNotIn('exam', store.completions())

    def test_undo_does_not_overwrite_reimported_course_and_history_is_bounded(self):
        with tempfile.TemporaryDirectory(dir=DATA) as directory:
            store = Store(directory); c = course(); store.save_course(c)
            store.mutate_with_undo('delete', {'id':c['id']})
            c['notes']='New notes'; store.save_course(c)
            with self.assertRaises(ValueError): store.undo()
            self.assertEqual(store.courses()[0]['notes'],'New notes')
            for i in range(25): store.mutate_with_undo('completion', {'id':str(i),'done':True})
            with store.connect() as db: self.assertEqual(db.execute('SELECT count(*) FROM undo_actions').fetchone()[0],20)

class AutoRefreshTests(unittest.TestCase):
    def test_refresh_scopes_to_current_term_records_logistics_and_throttles(self):
        with tempfile.TemporaryDirectory(dir=DATA) as directory:
            application=app.Application(directory)
            self.addCleanup(application.pool.shutdown)
            old=course(); application.store.save_course(old)
            past={**old,'id':'past','quarter':'Spring'}; application.store.save_course(past)
            fresh=course(); fresh['events'][0].update(time='6:30 pm',location='KNE 110')
            fresh['materials']=[{'url':'https://example.test/slides'}]
            now=dt.datetime(2026,10,21,tzinfo=dt.timezone.utc)
            with patch('app.importer.today_seattle',return_value=dt.date(2026,10,20)), patch.object(application,'import_course',return_value=fresh) as run:
                application.refresh_due_courses(now)
                application.refresh_due_courses(now+dt.timedelta(minutes=10))
                self.assertEqual(run.call_count,1)
                self.assertFalse(run.call_args.args[0]['scan_slides'])
            updates=application.store.get('refresh_updates')
            self.assertTrue(any('location changed' in change for change in updates[0]['changes']))
            self.assertTrue(any('new materials' in change for change in updates[0]['changes']))
            application.store.set('auto_refresh_enabled',False)
            with patch.object(application,'import_course') as run:
                application.refresh_due_courses(now+dt.timedelta(hours=1)); run.assert_not_called()

    def test_failed_refresh_retains_saved_course_and_reports_error(self):
        with tempfile.TemporaryDirectory(dir=DATA) as directory:
            application=app.Application(directory)
            self.addCleanup(application.pool.shutdown)
            old=course(); application.store.save_course(old)
            with patch('app.importer.today_seattle',return_value=dt.date(2026,10,20)), patch.object(application,'import_course',side_effect=OSError('offline')):
                application.refresh_due_courses()
            self.assertEqual(application.store.courses(),[old])
            self.assertEqual(application.store.get('refresh_updates')[0]['error'],'offline')
            self.assertFalse(application.store.get('auto_refresh_status')['running'])
