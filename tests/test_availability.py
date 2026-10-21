import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import app
from tracker.availability import AvailabilityChecker, CourseAvailabilityError, CATALOG_URL, offerings_url, parse_offerings

FIXTURES = Path(__file__).parent / 'fixtures' / 'availability'
TEST_DATA = Path(__file__).resolve().parents[1] / '.local-data' / 'tests'
TEST_DATA.mkdir(parents=True, exist_ok=True)


def listing_fetch(url):
    if url == CATALOG_URL:
        return (FIXTURES / 'catalog.html').read_bytes()
    if url == offerings_url('Autumn', 2026):
        return (FIXTURES / 'aut2026.html').read_bytes()
    raise urllib.error.HTTPError(url, 404, 'Not found', {}, None)


class AvailabilityTests(unittest.TestCase):
    def test_all_six_requested_courses_are_offered(self):
        checker = AvailabilityChecker()
        with patch('tracker.importer.fetch', side_effect=listing_fetch) as fetch:
            for code in ('CSE123', 'CSE311', 'CSE351', 'CSE331', 'CSE332', 'CSE312'):
                self.assertEqual(checker.validate(code, 'Autumn', 2026)['status'], 'offered')
            self.assertEqual(fetch.call_count, 1)

    def test_nonexistent_code_rejected_without_saving(self):
        with tempfile.TemporaryDirectory(dir=TEST_DATA) as directory:
            application = app.Application(directory)
            with patch('tracker.importer.fetch', side_effect=listing_fetch):
                with self.assertRaises(CourseAvailabilityError) as caught:
                    application.import_course({'code': 'CSE999', 'quarter': 'Autumn', 'year': 2026})
            self.assertEqual(caught.exception.code, 'course_not_found')
            self.assertEqual(caught.exception.source, CATALOG_URL)
            self.assertEqual(application.store.courses(), [])
            application.pool.shutdown()

    def test_known_course_not_offered_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_DATA) as directory:
            application = app.Application(directory)
            with patch('tracker.importer.fetch', side_effect=listing_fetch):
                with self.assertRaises(CourseAvailabilityError) as caught:
                    application.import_course({'code': 'CSE112', 'quarter': 'Autumn', 'year': 2026})
            self.assertEqual(caught.exception.code, 'not_offered')
            self.assertIn('not offered in Autumn 2026', str(caught.exception))
            self.assertEqual(application.store.courses(), [])
            application.pool.shutdown()

    def test_unpublished_quarter_is_unverified_not_not_offered(self):
        with patch('tracker.importer.fetch', side_effect=listing_fetch):
            with self.assertRaises(CourseAvailabilityError) as caught:
                AvailabilityChecker().validate('CSE312', 'Winter', 2030)
        self.assertEqual(caught.exception.code, 'offering_unverified')
        self.assertNotIn('is not offered', str(caught.exception))

    def test_login_and_wrong_quarter_pages_do_not_establish_offerings(self):
        for body in ('<h1>Sign in</h1>', (FIXTURES / 'aut2026.html').read_text()):
            with self.subTest(body=body[:25]):
                with self.assertRaises(ValueError):
                    parse_offerings(body, 'Winter', 2027)

    def test_offered_course_with_missing_website_is_not_saved(self):
        with tempfile.TemporaryDirectory(dir=TEST_DATA) as directory:
            application = app.Application(directory)
            with patch('tracker.importer.fetch', side_effect=listing_fetch):
                with self.assertRaises(CourseAvailabilityError) as caught:
                    application.import_course({'code': 'CSE312', 'quarter': 'Autumn', 'year': 2026})
            self.assertEqual(caught.exception.code, 'course_site_unavailable')
            self.assertIn('is listed for Autumn 2026', str(caught.exception))
            self.assertEqual(application.store.courses(), [])
            application.pool.shutdown()

    def test_network_failure_does_not_claim_course_is_nonexistent(self):
        with patch('tracker.importer.fetch', side_effect=OSError('offline')):
            with self.assertRaises(CourseAvailabilityError) as caught:
                AvailabilityChecker().validate('CSE312', 'Autumn', 2026)
        self.assertEqual(caught.exception.code, 'verification_unavailable')
