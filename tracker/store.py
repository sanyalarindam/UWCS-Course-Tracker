import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path


def data_directory():
    override = os.environ.get('UWCS_DATA_DIR')
    if override:
        return Path(override)
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'UWCS Tracker'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'UWCS Tracker'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'uwcs-tracker'


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else data_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'tracker.sqlite3'
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS courses(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS completions(id TEXT PRIMARY KEY, done INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS analyses(url TEXT PRIMARY KEY, body TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def courses(self):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT body FROM courses ORDER BY id')]

    def save_course(self, course):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO courses VALUES (?,?)', (course['id'], json.dumps(course)))

    def delete_course(self, course_id):
        with self.connect() as db:
            db.execute('DELETE FROM courses WHERE id=?', (course_id,))

    def completion(self, event_id, done):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO completions VALUES (?,?)', (event_id, bool(done)))

    def completions(self):
        with self.connect() as db:
            return {row[0]: bool(row[1]) for row in db.execute('SELECT * FROM completions')}

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))

    def analyses(self):
        with self.connect() as db:
            return {row[0]: json.loads(row[1]) for row in db.execute('SELECT * FROM analyses')}

    def save_analysis(self, url, analysis):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO analyses VALUES (?,?)', (url, json.dumps(analysis)))

    def export(self):
        return {'version': 1, 'courses': self.courses(), 'completions': self.completions(), 'analyses': self.analyses()}

    def restore(self, payload):
        if payload.get('version') != 1 or not isinstance(payload.get('courses'), list):
            raise ValueError('This is not a supported UWCS Tracker backup.')
        # Merge, rather than deleting existing local data.
        for course in payload['courses']:
            if not isinstance(course, dict) or not all(k in course for k in ('id', 'code', 'quarter', 'year', 'events', 'materials', 'essentials')):
                raise ValueError('Backup has an invalid course.')
        with self.connect() as db:
            for course in payload['courses']:
                db.execute('INSERT OR REPLACE INTO courses VALUES (?,?)', (course['id'], json.dumps(course)))
            for event_id, done in payload.get('completions', {}).items():
                db.execute('INSERT OR REPLACE INTO completions VALUES (?,?)', (event_id, bool(done)))
            for url, analysis in payload.get('analyses', {}).items():
                db.execute('INSERT OR REPLACE INTO analyses VALUES (?,?)', (url, json.dumps(analysis)))
