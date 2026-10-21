"""Validate courses against UW's catalog and public quarter offerings."""
import re
import threading
import time

from bs4 import BeautifulSoup

from tracker import importer

CATALOG_URL = 'https://www.washington.edu/students/crscat/cse.html'
TERM_CODES = {'Autumn': 'AUT', 'Winter': 'WIN', 'Spring': 'SPR', 'Summer': 'SUM'}


class CourseAvailabilityError(ValueError):
    def __init__(self, message, code, source):
        super().__init__(message)
        self.code = code
        self.source = source


def offerings_url(quarter, year):
    return f'https://www.washington.edu/students/timeschd/pub/{TERM_CODES[quarter]}{year}/cse.html'


def course_codes(soup):
    return {
        str(a.get('name') or a.get('id')).upper()
        for a in soup.select('a[name], a[id]')
        if re.fullmatch(r'cse\d{3}[a-z]?', str(a.get('name') or a.get('id')), re.I)
    }


def parse_catalog(html):
    soup = BeautifulSoup(html, 'html.parser')
    codes = course_codes(soup)
    if not codes or 'COMPUTER SCIENCE' not in importer.text(soup.find('h1')).upper():
        raise ValueError('The UW course catalog format was not recognized.')
    return codes


def parse_offerings(html, quarter, year):
    soup = BeautifulSoup(html, 'html.parser')
    heading = importer.text(soup.find('h1'))
    expected = f'{quarter} Quarter {year} Course Offerings'
    codes = course_codes(soup)
    if expected.lower() not in re.sub(r'\s+', ' ', heading).lower() or not codes:
        raise ValueError('The requested UW quarter offerings list could not be verified.')
    return codes


class AvailabilityChecker:
    """Short session cache prevents repeated downloads during course refreshes."""
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def get(self, url, parser):
        with self.lock:
            cached = self.cache.get(url)
            if cached and time.monotonic() - cached[0] < 900:
                return cached[1]
            parsed = parser(importer.fetch(url))
            self.cache[url] = (time.monotonic(), parsed)
            return parsed

    def validate(self, code, quarter, year):
        label = code.replace('CSE', 'CSE ', 1)
        source = offerings_url(quarter, year)
        # The quarter list can establish a historical offering even if the course
        # has since been removed from the current catalog.
        listing_error = None
        try:
            offered = self.get(source, lambda html: parse_offerings(html, quarter, year))
        except Exception as exc:
            offered, listing_error = None, exc
        if offered is not None and code in offered:
            return {'source': source, 'status': 'offered'}
        try:
            catalog = self.get(CATALOG_URL, parse_catalog)
        except Exception as exc:
            raise CourseAvailabilityError(
                'Could not verify this course with UW. Check your connection and try again. Nothing was added.',
                'verification_unavailable', CATALOG_URL,
            ) from exc
        # Some course websites use a letter suffix for a topic/section. A valid
        # parent catalog code is necessary, but does not prove that suffix runs.
        parent = re.sub(r'[A-Z]$', '', code) if code[-1:].isalpha() else code
        if code not in catalog and parent not in catalog:
            raise CourseAvailabilityError(
                f'Course not found: {label} is not listed in UW\'s CSE course catalog. Check the course code. Nothing was added.',
                'course_not_found', CATALOG_URL,
            )
        if offered is None:
            raise CourseAvailabilityError(
                f'Could not verify offerings for {quarter} {year}. The quarter listing may not be published yet or could not be reached. Nothing was added.',
                'offering_unverified', source,
            ) from listing_error
        if code != parent and parent in offered:
            # The requested topic still needs an independently verified website.
            return {'source': source, 'status': 'parent_offered'}
        raise CourseAvailabilityError(
            f'{label} is not offered in {quarter} {year} according to UW\'s published course offerings. Choose a different quarter. Nothing was added.',
            'not_offered', source,
        )
