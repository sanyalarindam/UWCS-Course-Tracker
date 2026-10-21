import datetime as dt
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import app
from tracker import importer
from tracker.store import Store
from http.server import ThreadingHTTPServer

FIXTURES = Path(__file__).parent / 'fixtures'
TEST_DATA = Path(__file__).resolve().parents[1] / '.local-data' / 'tests'
TEST_DATA.mkdir(parents=True, exist_ok=True)
URL = 'https://courses.cs.washington.edu/courses/cse312/26au/'
ARGS = {'code': 'CSE 312', 'quarter': 'Autumn', 'year': 2026}


def fixture_fetch(url):
    return (FIXTURES / ('syllabus.html' if 'syllabus' in url else 'cse312.html')).read_bytes()


class ImportTests(unittest.TestCase):
    def test_real_course_deadlines_and_materials(self):
        result = importer.parse_course(fixture_fetch(URL), URL, 'CSE312', 'Autumn', 2026)
        self.assertEqual(len(result['events']), 11)
        dates = {e['title']: e['date'] for e in result['events']}
        self.assertEqual(dates['PSet3'], '2026-10-21')
        self.assertEqual(dates['Midterm'], '2026-11-04')
        self.assertEqual(dates['PSet9'], '2026-12-11')
        first = next(e for e in result['events'] if e['title'] == 'PSet1')
        self.assertTrue(first['url'].endswith('/homework/pset1.pdf'))
        self.assertIsNone(first['time'])
        self.assertEqual(next(e for e in result['events'] if e['kind'] == 'exam' and 'Final' in e['title'])['time'], '12:30-2:20 pm')
        self.assertTrue(any(m['kind'] == 'slides' for m in result['materials']))

    def test_wrong_offering_rejected(self):
        with self.assertRaisesRegex(ValueError, 'does not confirm'):
            importer.parse_course(fixture_fetch(URL), URL, 'CSE312', 'Winter', 2026)

    def test_official_quarter_boundaries(self):
        terms = importer.parse_calendar((FIXTURES / 'calendar.html').read_bytes())
        for date, quarter, year, is_break in [(dt.date(2026, 9, 29), 'Autumn', 2026, True), (dt.date(2026, 9, 30), 'Autumn', 2026, False), (dt.date(2026, 12, 18), 'Autumn', 2026, False), (dt.date(2026, 12, 19), 'Winter', 2027, True), (dt.date(2027, 1, 4), 'Winter', 2027, False)]:
            term = importer.current_term(terms, date)
            self.assertEqual((term['quarter'], term['year'], term['in_break']), (quarter, year, is_break))
        self.assertIsNone(importer.current_term(terms, dt.date(2100, 1, 1)))

    def test_discovery_and_network_restrictions(self):
        self.assertEqual(importer.course_url('CSE 312', 'Autumn', 2026), URL)
        for bad in ['https://localhost/test', 'http://courses.cs.washington.edu/', 'https://courses.cs.washington.edu.evil.test/', 'https://courses.cs.washington.edu:8080/']:
            self.assertFalse(importer.allowed_url(bad))
        with self.assertRaises(ValueError):
            importer.course_url('../../etc', 'Autumn', 2026)

    def test_refresh_preserves_completion_notes_and_reports_changes(self):
        with tempfile.TemporaryDirectory(dir=TEST_DATA) as directory:
            application = app.Application(directory)
            with patch('tracker.importer.fetch', side_effect=fixture_fetch):
                c = application.import_course(ARGS)
                event = next(e for e in c['events'] if e['title'] == 'PSet3')
                application.store.completion(event['id'], True)
                c['notes'] = 'Ask about variance'
                application.store.save_course(c)
                original = fixture_fetch(URL)
                def changed(url):
                    return original.replace(b'(Wed, Oct 21)', b'(Wed, Oct 22)') if url == URL else fixture_fetch(url)
                with patch('tracker.importer.fetch', side_effect=changed):
                    refreshed = application.import_course(ARGS)
            updated = next(e for e in refreshed['events'] if e['title'] == 'PSet3')
            self.assertEqual(updated['changed_from'], '2026-10-21')
            self.assertTrue(application.store.completions()[event['id']])
            self.assertEqual(refreshed['notes'], 'Ask about variance')
            reopened = Store(directory)
            self.assertEqual(reopened.courses()[0]['notes'], 'Ask about variance')
            with tempfile.TemporaryDirectory(dir=TEST_DATA) as other:
                restored = Store(other)
                restored.restore(application.store.export())
                self.assertEqual(restored.courses(), reopened.courses())
                self.assertEqual(restored.completions(), reopened.completions())
            application.pool.shutdown()

    def test_404_saves_future_course_and_network_error_preserves_old(self):
        with tempfile.TemporaryDirectory(dir=TEST_DATA) as directory:
            application = app.Application(directory)
            error = urllib.error.HTTPError(URL, 404, 'Missing', {}, None)
            with patch('tracker.importer.fetch', side_effect=error):
                c = application.import_course(ARGS)
            self.assertEqual(c['status'], 'unavailable')
            with patch('tracker.importer.fetch', side_effect=fixture_fetch):
                c = application.import_course(ARGS)
            with patch('tracker.importer.fetch', side_effect=error):
                with self.assertRaisesRegex(ValueError, 'retained'):
                    application.import_course(ARGS)
            self.assertEqual(application.store.courses()[0]['events'], c['events'])
            application.pool.shutdown()

    def test_pdf_findings_have_page_sources_and_image_warning(self):
        class Page:
            def __init__(self, content): self.content = content
            def extract_text(self): return self.content
        class Reader:
            pages = [Page('Announcements\nHomework due Friday\nCheck Gradescope'), Page('')]
        with patch('pypdf.PdfReader', return_value=Reader()):
            result = importer.analyze_pdf(b'example', URL + 'slides/example.pdf')
        self.assertTrue(result['findings'])
        self.assertEqual(result['findings'][0]['page'], 1)
        self.assertTrue(result['findings'][0]['url'].endswith('#page=1'))
        self.assertTrue(all(f['status'] == 'Needs review' for f in result['findings']))
        self.assertNotIn('events', result)


class ServerTests(unittest.TestCase):
    def test_local_api_requires_mutation_token_and_serves_ui(self):
        with tempfile.TemporaryDirectory(dir=TEST_DATA) as directory:
            application = app.Application(directory)
            server = ThreadingHTTPServer(('127.0.0.1', 0), app.make_handler(application))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                with urllib.request.urlopen(base + '/') as response:
                    self.assertIn(b'Current courses', response.read())
                with urllib.request.urlopen(base + '/api/state') as response:
                    state = json.load(response)
                request = urllib.request.Request(base + '/api/complete', data=b'{"id":"test","done":true}', headers={'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request)
                self.assertEqual(caught.exception.code, 403)
                request.add_header('X-UWCS-Token', state['token'])
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 200)
                self.assertTrue(application.store.completions()['test'])
                evil = urllib.request.Request(base + '/api/state', headers={'Host':'evil.example'})
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(evil)
            finally:
                server.shutdown()
                server.server_close()
                application.pool.shutdown()


if __name__ == '__main__':
    unittest.main()
