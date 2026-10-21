"""Public UW course discovery, date extraction, and local slide analysis."""
import datetime as dt
import hashlib
import io
import re
import urllib.error
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

CALENDAR_URL = 'https://www.washington.edu/students/reg/begendcal.html'
QUARTERS = {'Winter': 'wi', 'Spring': 'sp', 'Summer': 'su', 'Autumn': 'au'}
MONTHS = {m.lower(): i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}


def today_seattle():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo('America/Los_Angeles')).date()
    except Exception:
        # Windows may not have the IANA database. Pacific DST starts/ends on Sundays.
        now = dt.datetime.now(dt.timezone.utc)
        march = dt.date(now.year, 3, 8)
        november = dt.date(now.year, 11, 1)
        start = dt.datetime.combine(march + dt.timedelta(days=(6-march.weekday()) % 7), dt.time(10), dt.timezone.utc)
        end = dt.datetime.combine(november + dt.timedelta(days=(6-november.weekday()) % 7), dt.time(9), dt.timezone.utc)
        return (now + dt.timedelta(hours=-7 if start <= now < end else -8)).date()


def allowed_url(url):
    p = urllib.parse.urlsplit(url)
    return p.scheme == 'https' and p.hostname in {'courses.cs.washington.edu', 'www.washington.edu'} and not p.username and p.port in (None, 443)


class UWRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise ValueError('Redirect left the supported public UW hosts.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, limit=25_000_000):
    if not allowed_url(url):
        raise ValueError('Only public HTTPS pages on courses.cs.washington.edu and www.washington.edu can be downloaded.')
    request = urllib.request.Request(url, headers={'User-Agent': 'UWCS-Tracker/0.1 (personal course agenda)'})
    with urllib.request.build_opener(UWRedirect()).open(request, timeout=25) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Document is too large for local analysis (25 MB limit).')
        return data


def parse_date(text, year):
    iso = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', text)
    if iso:
        try:
            return dt.date.fromisoformat(iso[1]).isoformat()
        except ValueError:
            return None
    numeric = re.search(r'(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)', text)
    if numeric:
        try:
            return dt.date(year, int(numeric[1]), int(numeric[2])).isoformat()
        except ValueError:
            return None
    reverse = re.search(r'\b(\d{1,2})\s+(Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Jun\w*|Jul\w*|Aug\w*|Sep\w*|Oct\w*|Nov\w*|Dec\w*)\b', text, re.I)
    if reverse:
        text = f'{reverse[2]} {reverse[1]}'
    match = re.search(r'\b(Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Jun\w*|Jul\w*|Aug\w*|Sep\w*|Oct\w*|Nov\w*|Dec\w*)\.?\s+(\d{1,2})(?:\s*,\s*(20\d{2}))?', text, re.I)
    if not match:
        return None
    try:
        return dt.date(int(match[3] or year), MONTHS[match[1][:3].lower()], int(match[2])).isoformat()
    except ValueError:
        return None


def parse_calendar(html):
    soup = BeautifulSoup(html, 'html.parser')
    terms = []
    for row in soup.select('tr'):
        cells = row.find_all(['th', 'td'], recursive=False)
        if len(cells) < 4:
            continue
        match = re.fullmatch(r'(Autumn|Winter|Spring|Summer) (20\d{2})', cells[0].get_text(' ', strip=True))
        if not match:
            continue
        quarter, year = match[1], int(match[2])
        start = parse_date(cells[1].get_text(' ', strip=True), year)
        end = parse_date(cells[2].get_text(' ', strip=True), year)
        finals = cells[3].get_text(' ', strip=True)
        # A finals range such as Dec 12-18, 2026 ends on Dec 18.
        expanded = re.sub(r'(\d{1,2})\s*[-–]\s*(\d{1,2})', r'\2', finals)
        end = parse_date(expanded, year) or end
        if start and end:
            terms.append({'quarter': quarter, 'year': year, 'start': start, 'end': end})
    return sorted(terms, key=lambda t: t['start'])


def current_term(terms, today=None):
    date = (today or today_seattle()).isoformat()
    for term in terms:
        if term['start'] <= date <= term['end']:
            return {**term, 'in_break': False}
    for term in terms:
        if term['start'] > date:
            return {**term, 'in_break': True}
    return None


def course_url(code, quarter, year):
    clean = re.sub(r'\s+', '', code).lower()
    if not re.fullmatch(r'cse\d{3}[a-z]?', clean):
        raise ValueError('Enter a CSE course code such as CSE 312 or CSE 390A.')
    if quarter not in QUARTERS or not 2000 <= int(year) <= 2100:
        raise ValueError('Choose a valid quarter and year (2000–2100).')
    return f'https://courses.cs.washington.edu/courses/{clean}/{int(year) % 100:02d}{QUARTERS[quarter]}/'


def text(node):
    return node.get_text(' ', strip=True) if node else ''


def safe_link(base, href):
    url = urllib.parse.urljoin(base, href)
    return url if urllib.parse.urlsplit(url).scheme in ('https', 'http') else base


def parse_course(html, url, code, quarter, year):
    from tracker.courses import verify_offering, parse_layout
    from tracker.exams import logistics
    soup = BeautifulSoup(html, 'html.parser')
    title = verify_offering(soup, code, quarter, year)
    adapted = parse_layout(soup, url, code, quarter, year)
    if adapted is not None:
        return adapted
    events, materials, essentials = [], [], []
    releases = {}
    for a in soup.select('a[href]'):
        label, href = text(a), a['href']
        if re.search(r'syllabus|gradescope|office hours|course.?staff|discussion|AI policy', label, re.I):
            entry = {'label': label, 'url': safe_link(url, href)}
            if entry not in essentials:
                essentials.append(entry)
        release = re.match(r'(PSet\s*\d+|HW\s*\d+|Homework\s*\d+)\s+Out', label, re.I)
        if release:
            releases[re.sub(r'\s', '', release[1]).lower()] = safe_link(url, href)
    rows = soup.select('.day') or soup.select('tr')
    dated_rows = 0
    for row in rows:
        date = parse_date(text(row.select_one('.date')) or text(row), year)
        if not date:
            continue
        dated_rows += 1
        kind = text(row.select_one('.type'))
        topic = text(row.select_one('.topic'))
        if not kind and row.find(['td', 'th']):
            topic = text(row)
        for a in row.select('a[href]'):
            label = text(a)
            target = safe_link(url, a['href'])
            due = re.search(r'\b(due|deadline)\b', label, re.I)
            if due:
                name = re.sub(r'\s*(due|deadline)\s*:?\s*', '', label, flags=re.I).strip() or label
                assignment = releases.get(re.sub(r'\s', '', name).lower(), target)
                events.append({'title': name, 'date': date, 'kind': 'assignment', 'url': assignment, 'source': url, 'time': None})
            elif not re.search(r'\bOut\b', label, re.I):
                material_kind = 'slides' if 'slide' in label.lower() else 'reading' if 'reading' in label.lower() else 'recording' if 'recording' in label.lower() else 'section'
                if a['href'] != '#':
                    materials.append({'title': f'{kind}: {topic}' if kind else topic or label, 'label': label, 'date': date, 'kind': material_kind, 'url': target})
        if re.search(r'\b(midterm|final exam)\b', kind or topic, re.I):
            clock = re.search(r'\b\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)', text(row), re.I)
            events.append({'title': kind or 'Exam', 'date': date, 'kind': 'exam', 'url': url, 'source': url, **logistics(text(row))})
    # Deduplicate without discarding the original source or inventing due times.
    events = list({(e['title'], e['date'], e['kind']): e for e in events}.values())
    materials = list({(m['url'], m['date']): m for m in materials}.values())
    warnings = ['Future course materials and dates may be tentative. Due times are unspecified unless explicitly verified.']
    if not events:
        warnings.append('No supported deadline or exam entries found. This page format needs review; an empty agenda does not mean no assignments.')
    return {'title': title, 'events': events, 'materials': materials, 'essentials': essentials, 'warnings': warnings, 'dated_rows': dated_rows}


def analyze_pdf(data, url):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) > 350:
        raise ValueError('Slide deck exceeds the 350-page analysis limit.')
    findings, nonempty = [], 0
    for number, page in enumerate(reader.pages, 1):
        content = page.extract_text() or ''
        nonempty += bool(content.strip())
        lines = [re.sub(r'\s+', ' ', line).strip() for line in content.splitlines() if line.strip()]
        for i, line in enumerate(lines):
            if re.search(r'\b(due|deadline|midterm|final exam|office hours|announcement|reminder|homework|problem set)\b', line, re.I):
                snippet = ' '.join(lines[max(0, i-1):i+3])[:650]
                if not any(f['text'] == snippet for f in findings):
                    findings.append({'page': number, 'text': snippet, 'url': f'{url}#page={number}', 'status': 'Needs review'})
        if len(findings) >= 80:
            break
    return {'pages': len(reader.pages), 'findings': findings, 'hash': hashlib.sha256(data).hexdigest(), 'warning': 'Scanned or image-only slides need OCR, which is not included yet.' if nonempty < len(reader.pages) / 2 else '', 'method': 'Local text extraction and keyword review; findings are not confirmed deadlines.'}
