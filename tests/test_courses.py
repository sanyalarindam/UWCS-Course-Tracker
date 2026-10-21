"""Regression coverage for the six requested Autumn 2026 offerings."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app
from tracker.courses import COURSES, load_course

FIXTURES = Path(__file__).parent / 'fixtures' / 'courses'
TEST_DATA = Path(__file__).resolve().parents[1] / '.local-data' / 'tests'
TEST_DATA.mkdir(parents=True, exist_ok=True)
EXPECTED = {
    'CSE123': (8, 'P0 Ciphers', '2026-10-21'),
    'CSE311': (11, 'HW1', '2026-10-08'),
    'CSE351': (68, 'Lab1b', '2026-10-21'),
    'CSE331': (14, 'Homework 0', '2026-10-02'),
    'CSE332': (17, 'EX0 Generics', '2026-10-09'),
    'CSE312': (11, 'PSet3', '2026-10-21'),
}


def fixture_fetch(url):
    manifest = json.loads((FIXTURES / 'manifest.json').read_text())
    if url not in manifest:
        raise ValueError('No fixture for ' + url)
    return (FIXTURES / manifest[url]).read_bytes()


class CourseSelectionTests(unittest.TestCase):
    def test_new_workspace_is_empty_and_does_not_fetch_any_course(self):
        with tempfile.TemporaryDirectory(dir=TEST_DATA) as directory:
            with patch('tracker.importer.fetch') as fetch:
                application = app.Application(directory)
                state = application.state()
                self.assertEqual(state['courses'], [])
                self.assertEqual(state['completions'], {})
                self.assertEqual(state['analyses'], {})
                self.assertEqual({c['code'] for c in state['catalog']}, set(EXPECTED))
                fetch.assert_not_called()
                application.pool.shutdown()

    def test_choosing_one_course_does_not_import_the_catalog(self):
        with tempfile.TemporaryDirectory(dir=TEST_DATA) as directory:
            application = app.Application(directory)
            with patch('tracker.importer.fetch', side_effect=fixture_fetch):
                application.import_course({'code': 'CSE 331', 'quarter': 'Autumn', 'year': 2026})
            self.assertEqual([c['code'] for c in application.state()['courses']], ['CSE331'])
            reopened = app.Application(directory)
            self.assertEqual([c['code'] for c in reopened.state()['courses']], ['CSE331'])
            application.pool.shutdown()
            reopened.pool.shutdown()


class CourseFormatTests(unittest.TestCase):
    def test_all_six_course_formats(self):
        for code, (count, title, date) in EXPECTED.items():
            with self.subTest(code=code), patch('tracker.importer.fetch', side_effect=fixture_fetch):
                url = app.importer.course_url(code, 'Autumn', 2026)
                course = load_course(fixture_fetch(url), url, code, 'Autumn', 2026)
                self.assertEqual(len(course['events']), count)
                found = next(e for e in course['events'] if e['title'] == title)
                self.assertEqual(found['date'], date)
                self.assertTrue(course['materials'])
                self.assertTrue(all(e['source'].startswith(url) for e in course['events']))
                self.assertFalse(any(w.startswith('No supported') for w in course['warnings']))

    def test_quiz_signup_windows_are_not_deadlines_and_reviews_are_not_exams(self):
        with patch('tracker.importer.fetch', side_effect=fixture_fetch):
            for code in ('CSE123', 'CSE332'):
                url = app.importer.course_url(code, 'Autumn', 2026)
                course = load_course(fixture_fetch(url), url, code, 'Autumn', 2026)
                self.assertFalse(any(e['title'].startswith('CQ') for e in course['events']))
                self.assertFalse(any('review' in e['title'].lower() for e in course['events'] if e['kind'] == 'exam'))
                if code == 'CSE123':
                    self.assertEqual(next(e for e in course['events'] if e['title'] == 'P0 Ciphers')['time'], '11:59PM PT')

    def test_future_deadlines_without_published_links_are_retained(self):
        code = 'CSE351'
        url = app.importer.course_url(code, 'Autumn', 2026)
        with patch('tracker.importer.fetch', side_effect=fixture_fetch):
            course = load_course(fixture_fetch(url), url, code, 'Autumn', 2026)
        assignment = next(e for e in course['events'] if e['title'] == 'HW25')
        self.assertEqual(assignment['date'], '2026-12-09')
        self.assertIsNone(assignment['time'])
        self.assertEqual(assignment['url'], url + 'schedule.html')

    def test_wrong_term_still_rejected_for_each_format(self):
        for code in EXPECTED:
            with self.subTest(code=code), patch('tracker.importer.fetch', side_effect=fixture_fetch):
                url = app.importer.course_url(code, 'Autumn', 2026)
                with self.assertRaises(ValueError):
                    load_course(fixture_fetch(url), url, code, 'Winter', 2026)


if __name__ == '__main__':
    unittest.main()
