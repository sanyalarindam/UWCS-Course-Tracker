"""Run with python app.py. No account, hosted backend, or external AI service."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import secrets
import sys
import threading
import urllib.error
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.deps'))
try:
    from tracker import importer
    from tracker.store import Store
    from tracker.courses import COURSES, load_course
    from tracker.availability import AvailabilityChecker, CourseAvailabilityError
except ImportError:
    raise SystemExit('Install dependencies first: python -m pip install --target .deps -r requirements.txt')


class Application:
    def __init__(self, directory=None):
        self.store = Store(directory)
        self.token = secrets.token_urlsafe(32)
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.jobs = {}
        self.lock = threading.Lock()
        self.availability = AvailabilityChecker()
        if not self.store.get('terms'):
            seed = ROOT / 'data' / 'calendar.json'
            if seed.exists():
                self.store.set('terms', json.loads(seed.read_text()))

    def state(self):
        today = importer.today_seattle()
        return {'courses': self.store.courses(), 'catalog': COURSES, 'completions': self.store.completions(), 'analyses': self.store.analyses(), 'term': importer.current_term(self.store.get('terms', []), today), 'terms': self.store.get('terms', []), 'today': today.isoformat(), 'data_path': str(self.store.directory), 'calendar_checked': self.store.get('calendar_checked'), 'calendar_source': importer.CALENDAR_URL, 'preferences': {'theme': self.store.get('theme', 'system')}, 'token': self.token}

    def job(self, fn):
        key = secrets.token_hex(8)
        with self.lock:
            self.jobs[key] = {'status': 'running'}
        def work():
            try:
                result = {'status': 'done', 'result': fn()}
            except Exception as exc:
                result = {'status': 'error', 'error': str(exc), 'error_code': getattr(exc, 'code', None), 'source': getattr(exc, 'source', None)}
            with self.lock:
                self.jobs[key] = result
        self.pool.submit(work)
        return {'job': key}

    def import_course(self, args):
        code = ''.join(args['code'].upper().split())
        quarter, year = args['quarter'], int(args['year'])
        url = importer.course_url(code, quarter, year)
        course_id = f'{code}-{year}-{quarter}'
        previous = next((c for c in self.store.courses() if c['id'] == course_id), None)
        availability = self.availability.validate(code, quarter, year)
        course = previous or {'id': course_id, 'code': code, 'quarter': quarter, 'year': year, 'url': url, 'title': code, 'events': [], 'materials': [], 'essentials': [], 'notes': '', 'warnings': []}
        try:
            html = importer.fetch(url).decode('utf-8', errors='replace')
            parsed = load_course(html, url, code, quarter, year)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                retained = ' Your saved course and agenda have been retained.' if previous else ' Nothing was added.'
                raise CourseAvailabilityError(
                    f'{code.replace("CSE", "CSE ", 1)} is listed for {quarter} {year}, but its public course website or linked calendar is unavailable.' + retained,
                    'course_site_unavailable', availability['source'],
                ) from exc
            raise
        old = {e['id']: e for e in course.get('events', [])}
        for event in parsed['events']:
            identity = f"{course_id}|{event['kind']}|{event['title']}"
            event['id'] = hashlib.sha256(identity.encode()).hexdigest()[:20]
            prior = old.get(event['id'])
            event['changed_from'] = prior['date'] if prior and prior['date'] != event['date'] else (prior or {}).get('changed_from')
        course.update(parsed)
        course['availability'] = availability
        course.update(status='ready' if parsed['events'] else 'review', checked=dt.datetime.now(dt.timezone.utc).isoformat())
        syllabus = next((e['url'] for e in parsed['essentials'] if 'syllabus' in e['label'].lower()), None)
        if syllabus:
            try:
                from bs4 import BeautifulSoup
                content = BeautifulSoup(importer.fetch(syllabus), 'html.parser')
                course['policies'] = [{'text': li.get_text(' ', strip=True), 'url': syllabus} for li in content.select('li') if any(w in li.get_text().lower() for w in ('due', 'late days', 'final exam', 'midterm'))][-15:]
            except Exception as exc:
                course['warnings'].append(f'Syllabus could not be refreshed: {exc}')
        self.store.save_course(course)
        # Recent slides are analyzed locally; older decks remain available on demand.
        if args.get('scan_slides'):
            recent = sorted([m for m in course['materials'] if m['kind'] == 'slides' and urllib.parse.urlsplit(m['url']).path.lower().endswith('.pdf') and m['date'] <= importer.today_seattle().isoformat()], key=lambda m: m['date'], reverse=True)[:2]
            for material in recent:
                try:
                    self.analyze({'course': course_id, 'url': material['url']})
                except Exception as exc:
                    course['warnings'].append(f"Slide analysis unavailable for {material['date']}: {exc}")
            course['scan_slides'] = True
            self.store.save_course(course)
        return course

    def analyze(self, args):
        course = next((c for c in self.store.courses() if c['id'] == args['course']), None)
        if not course:
            raise ValueError('Course not found.')
        url = args['url']
        if not any(m['url'] == url and m['kind'] == 'slides' for m in course['materials']):
            raise ValueError('Select a linked slide deck from this course.')
        if not urllib.parse.urlsplit(url).path.lower().endswith('.pdf'):
            raise ValueError('This first version supports PDF slide decks. Open the source for other formats.')
        data = importer.fetch(url)
        prior = self.store.analyses().get(url)
        digest = hashlib.sha256(data).hexdigest()
        if prior and prior.get('hash') == digest:
            return prior
        result = importer.analyze_pdf(data, url)
        result['checked'] = dt.datetime.now(dt.timezone.utc).isoformat()
        cache = self.store.directory / 'slides'
        cache.mkdir(exist_ok=True)
        (cache / f'{digest}.pdf').write_bytes(data)
        self.store.save_analysis(url, result)
        return result

    def refresh_calendar(self):
        terms = importer.parse_calendar(importer.fetch(importer.CALENDAR_URL))
        if not terms:
            raise ValueError('UW calendar format was not recognized. Retaining the cached calendar.')
        self.store.set('terms', terms)
        self.store.set('calendar_checked', dt.datetime.now(dt.timezone.utc).isoformat())
        return {'terms': len(terms)}


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, data, status=200, content_type='application/json'):
            raw = data if isinstance(data, bytes) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def valid_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def do_GET(self):
            if not self.valid_host():
                return self.send({'error': 'Invalid local host.'}, 403)
            path = urllib.parse.urlsplit(self.path).path
            if path == '/api/state':
                return self.send(app.state())
            if path == '/api/export':
                return self.send(app.store.export())
            if path.startswith('/api/jobs/'):
                with app.lock:
                    result = app.jobs.get(path.rsplit('/', 1)[-1], {'status': 'error', 'error': 'Unknown job.'})
                return self.send(result)
            if path.startswith('/api/slides/'):
                name = path.rsplit('/', 1)[-1]
                import re
                if re.fullmatch(r'[a-f0-9]{64}\.pdf', name):
                    cached = app.store.directory / 'slides' / name
                    if cached.exists():
                        return self.send(cached.read_bytes(), content_type='application/pdf')
                return self.send({'error': 'Cached PDF not found'}, 404)
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/theme.js': ('theme.js', 'text/javascript; charset=utf-8'), '/styles.css': ('styles.css', 'text/css; charset=utf-8')}
            if path in files:
                name, mime = files[path]
                content = (ROOT / 'web' / name).read_bytes()
                if path == '/':
                    preference = app.store.get('theme', 'system')
                    if preference not in ('system', 'light', 'dark'):
                        preference = 'system'
                    content = content.replace(b'<html lang="en">', f'<html lang="en" data-theme-preference="{preference}">'.encode())
                return self.send(content, content_type=mime)
            return self.send({'error': 'Not found'}, 404)

        def do_POST(self):
            if not self.valid_host() or self.headers.get('X-UWCS-Token') != app.token:
                return self.send({'error': 'Invalid local session. Reload the app.'}, 403)
            try:
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= 10_000_000:
                    raise ValueError('Request must be between 1 byte and 10 MB.')
                args = json.loads(self.rfile.read(size))
                if self.path == '/api/courses':
                    importer.course_url(args['code'], args['quarter'], int(args['year']))
                    return self.send(app.job(lambda: app.import_course(args)), 202)
                if self.path == '/api/analyze':
                    return self.send(app.job(lambda: app.analyze(args)), 202)
                if self.path == '/api/calendar':
                    return self.send(app.job(app.refresh_calendar), 202)
                if self.path == '/api/preferences':
                    if args.get('theme') not in ('system', 'light', 'dark'):
                        raise ValueError('Choose system, light, or dark appearance.')
                    app.store.set('theme', args['theme'])
                elif self.path == '/api/complete':
                    app.store.completion(args['id'], args['done'])
                elif self.path == '/api/notes':
                    course = next(c for c in app.store.courses() if c['id'] == args['id'])
                    course['notes'] = str(args['notes'])[:20000]
                    app.store.save_course(course)
                elif self.path == '/api/delete':
                    app.store.delete_course(args['id'])
                elif self.path == '/api/restore':
                    app.store.restore(args)
                else:
                    return self.send({'error': 'Not found'}, 404)
                return self.send({'ok': True})
            except (ValueError, KeyError, TypeError, StopIteration) as exc:
                return self.send({'error': str(exc) or 'Invalid request.'}, 400)
            except Exception as exc:
                return self.send({'error': str(exc)}, 500)
    return Handler


def main():
    parser = argparse.ArgumentParser(description='UWCS Tracker — private local course agenda')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--desktop', action='store_true', help='Use an optional pywebview desktop window')
    args = parser.parse_args()
    app = Application(args.data_dir)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(app))
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'UWCS Tracker: {url}\nLocal data: {app.store.directory}\nPress Ctrl+C to stop.', flush=True)
    if args.desktop:
        try:
            import webview
        except ImportError:
            raise SystemExit('For a desktop window, install pywebview: python -m pip install pywebview')
        threading.Thread(target=server.serve_forever, daemon=True).start()
        webview.create_window('UWCS Tracker', url, width=1360, height=900, min_size=(820, 620))
        webview.start()
        server.shutdown()
    else:
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    server.server_close()
    app.pool.shutdown(wait=False, cancel_futures=True)


if __name__ == '__main__':
    main()
