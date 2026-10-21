"""Bounded discovery and adapters for the public UW course calendar formats.

Scripts are read as configuration only, never executed. Dates come from explicit
calendar entries or the end of an HTML table's stated assignment span.
"""
import re
import urllib.parse

from bs4 import BeautifulSoup

from tracker import importer as core
from tracker.exams import logistics

COURSES = [
    {'code': 'CSE123', 'name': 'Introduction to Computer Programming III'},
    {'code': 'CSE311', 'name': 'Foundations of Computing I'},
    {'code': 'CSE351', 'name': 'The Hardware/Software Interface'},
    {'code': 'CSE331', 'name': 'Software Design & Implementation'},
    {'code': 'CSE332', 'name': 'Data Structures and Parallelism'},
    {'code': 'CSE312', 'name': 'Foundations of Computing II'},
]


def verify_offering(soup, code, quarter, year):
    identity = re.compile(r'\bcse\s*' + re.escape(re.sub(r'\s+', '', code)[3:]) + r'\b', re.I)
    headings = [core.text(e) for e in soup.select('h1, title, .doc-title, [data-course-identity]')]
    identities = [h for h in headings if identity.search(h)]
    term = f'{year % 100:02d}{core.QUARTERS[quarter]}'
    raw = str(soup)
    evidence = bool(re.search(r'(?<![a-z0-9])' + term + r'(?![a-z0-9])', raw, re.I)) or bool(re.search(r'\b' + quarter + r'\s+' + str(year) + r'\b', core.text(soup), re.I))
    # Explicit course-header terms override unrelated links to another offering.
    for heading in identities:
        explicit = re.search(r'\b(Autumn|Winter|Spring|Summer)\s+(20\d{2})\b', heading, re.I)
        if explicit and (explicit[1].lower(), int(explicit[2])) != (quarter.lower(), year):
            evidence = False
    if not identities or not evidence:
        raise ValueError('The page title does not confirm the requested course, quarter, and year. Import stopped for review.')
    meaningful = next((h for h in identities if ':' in h and not re.search(r'\b(schedule|calendar)\b', h, re.I)), None)
    name = next((c['name'] for c in COURSES if c['code'] == code.upper().replace(' ', '')), None)
    return meaningful or (f'{code}: {name}, {quarter} {year}' if name else identities[0])


def essentials(soup, url):
    found = {}
    for a in soup.select('a[href]'):
        label = core.text(a)
        if re.search(r'syllabus|gradescope|office hours|course.?staff|discussion|AI policy|canvas|assignments|exams|^staff$|^course info$', label, re.I):
            target = core.safe_link(url, a['href'])
            found[target] = {'label': label, 'url': target}
    return list(found.values())


def clock(node):
    match = re.search(r'\b\d{1,2}:\d{2}(?:\s*[-–]\s*\d{1,2}:\d{2})?\s*(?:[ap]\.?m\.?(?:\s*(?:PT|PST|PDT))?)?', core.text(node), re.I)
    return match[0].strip() if match else None


def event(title, date, node, url, kind='assignment', time=None):
    a = node if node.name == 'a' and node.get('href') else node.select_one('a[href]')
    return {'title': re.sub(r'\s*\b(due|deadline)\b\s*:?\s*', '', title, flags=re.I).strip(), 'date': date, 'kind': kind, 'time': time if time else clock(node), 'url': core.safe_link(url, a['href']) if a else url, 'source': url, **({'location': logistics(core.text(node))['location']} if kind == 'exam' else {})}


def material(a, date, title, url, lecture=False):
    label, href = core.text(a), a.get('href', '')
    if not href or href.startswith('#'):
        return None
    target = core.safe_link(url, href)
    path = urllib.parse.urlsplit(target).path.lower()
    if 'slide' in label.lower() or (lecture and path.endswith(('.pdf', '.pptx', '.ppt'))):
        kind = 'slides'
    elif 'reading' in label.lower() or 'pre-class' in label.lower():
        kind = 'reading'
    elif 'recording' in label.lower() or 'panopto' in target:
        kind = 'recording'
    else:
        kind = 'section'
    return {'title': title, 'label': label, 'date': date, 'kind': kind, 'url': target}


def result(soup, url, code, quarter, year, events, materials, count):
    events = list({(e['title'], e['date'], e['kind'], e['time']): e for e in events}.values())
    materials = list({(m['url'], m['date']): m for m in materials if m}.values())
    warnings = ['Future course materials and dates may be tentative. Due times are unspecified unless explicitly verified.']
    if not events:
        warnings.append('No supported deadline or exam entries found. Check the original course calendar before relying on an empty agenda.')
    return {'title': verify_offering(soup, code, quarter, year), 'events': events, 'materials': materials, 'essentials': essentials(soup, url), 'warnings': warnings, 'dated_rows': count}


def parse_layout(soup, url, code, quarter, year):
    if soup.select('tr.calendar-row'):
        return parse_intro(soup, url, code, quarter, year)
    if soup.select('td.eventtd[id]'):
        return parse_month_grid(soup, url, code, quarter, year)
    if soup.select('.sched-day'):
        return parse_schedule(soup, url, code, quarter, year)
    if soup.select('.day[date]'):
        return parse_attribute_grid(soup, url, code, quarter, year)
    return None


def parse_intro(soup, url, code, quarter, year):
    events, materials = [], []
    rows = soup.select('table tr')
    dates, current = [], None
    for row in rows:
        label = row.select_one('.class-date')
        if label:
            current = core.parse_date(core.text(label), year)
        dates.append(current)
    for i, row in enumerate(rows):
        date = dates[i]
        if not date:
            continue
        title = core.text(row.select_one('.class-title-text'))
        label = core.text(row.select_one('.class-title-label'))
        if re.match(r'(QUIZ|EXAM)\b', label):
            events.append(event(title or label, date, row.select_one('.class-data') or row, url, 'exam'))
        for a in row.select('.class-resources a[href]'):
            materials.append(material(a, date, f'{label}: {title}', url, lecture=label.startswith('LES')))
        for project in row.select('td.assignment'):
            boundary = project.select_one('.assignment-due')
            if not boundary or not re.search(r'\b(by|due|deadline)\b', core.text(boundary), re.I):
                continue  # An open quiz window is not a submission deadline.
            end = i + int(project.get('rowspan', 1)) - 1
            due = dates[end] if end < len(dates) else None
            if not due:
                continue
            name = core.text(project.select_one('.assignment-text'))
            events.append(event(name, due, project, url, time=clock(project.select_one('.assignment-due'))))
    return result(soup, url, code, quarter, year, events, materials, len(soup.select('tr.calendar-row')))


def parse_month_grid(soup, url, code, quarter, year):
    events, materials = [], []
    cells = soup.select('td.eventtd[id]')
    for cell in cells:
        date = core.parse_date(cell['id'], year)
        if not date:
            continue
        for entry in cell.find_all('div', recursive=False):
            classes = entry.get('class', [])
            label = core.text(entry.select_one('.summary'))
            if 'hw' in classes and re.search(r'\bdue\b', label, re.I):
                events.append(event(label, date, entry, url))
            elif 'exam' in classes:
                events.append(event(label, date, entry, url, 'exam'))
            elif 'lecture' in classes or 'section' in classes:
                title = core.text(entry.select_one('.description')) or label
                for a in entry.select('a[href]'):
                    materials.append(material(a, date, title, url, lecture='lecture' in classes))
    return result(soup, url, code, quarter, year, events, materials, len(cells))


def parse_schedule(soup, url, code, quarter, year):
    events, materials = [], []
    rows = soup.select('.sched-day')
    for row in rows:
        date = core.parse_date(core.text(row.select_one('.sched-date')), year)
        if not date:
            continue
        topic = core.text(row.select_one('.sched-topic-title'))
        for a in row.select('.sched-assignment a'):
            if re.search(r'\bdue\b', core.text(a), re.I):
                events.append(event(core.text(a), date, a, url))
        if 'exam' in row.get('class', []) or re.search(r'\bEXAM\b', topic):
            name = re.sub(r'^EXAM\s*', '', topic).strip()
            events.append(event(name, date, row.select_one('.sched-topic') or row, url, 'exam'))
        quiz = re.search(r'\bQuiz\s+\d+', topic, re.I)
        if quiz:
            events.append(event(quiz[0], date, row.select_one('.sched-topic'), url, 'exam'))
        reading = row.select_one('.sched-topic-materials')
        if reading and not reading.select('a[href]'):
            materials.append({'title': topic, 'label': core.text(reading), 'date': date, 'kind': 'reading', 'url': url})
        for a in row.select('.sched-topic a[href]'):
            materials.append(material(a, date, topic, url, lecture=True))
    return result(soup, url, code, quarter, year, events, materials, len(rows))


def parse_attribute_grid(soup, url, code, quarter, year):
    events, materials = [], []
    rows = soup.select('.day[date]')
    for row in rows:
        date = core.parse_date(row['date'], year)
        if not date:
            continue
        for assignment in row.select('.assignment'):
            events.append(event(core.text(assignment), date, assignment, url))
        for exam in row.select('.exam'):
            if not re.search(r'review|practice', core.text(exam), re.I):
                events.append(event(core.text(exam), date, exam, url, 'exam'))
        for block in row.select('details'):
            topic = core.text(block.select_one('summary'))
            for a in block.select('a[href]'):
                materials.append(material(a, date, topic, url, lecture='lecture' in block.get('class', [])))
    return result(soup, url, code, quarter, year, events, materials, len(rows))


def load_course(html, url, code, quarter, year):
    """Follow only declared configuration/navigation and at most two schedule links."""
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup.select('script[src]'):
        config_url = core.safe_link(url, script['src'])
        if config_url.startswith(url) and config_url.endswith('/site/js/config.js'):
            config = core.fetch(config_url).decode('utf-8')
            number = re.search(r'const\s+courseNumber\s*=\s*[\"\']([^\"\']+)', config)
            term = re.search(r'const\s+quarter\s*=\s*[\"\']([^\"\']+)', config)
            expected = f'{year % 100:02d}{core.QUARTERS[quarter]}'
            if not number or not term or number[1].replace(' ', '').upper() != code or term[1] != expected:
                raise ValueError('Course configuration does not confirm the requested offering.')
            identity = soup.new_tag('div', attrs={'data-course-identity': ''})
            identity.string = f'{number[1]}, {quarter} {year}'
            soup.append(identity)
            if re.search(r'fileName:\s*[\"\']top-nav\.html', config):
                nav = BeautifulSoup(core.fetch(urllib.parse.urljoin(config_url, '../top-nav.html')), 'html.parser')
                for a in nav.select('a[href]'):
                    a['href'] = core.safe_link(url, a['href'])
                soup.append(nav)
    documents = [(soup, url)]
    if not soup.select('.day, .sched-day, tr.calendar-row, td.eventtd[id]'):
        links = []
        for a in soup.select('a[href]'):
            if not re.search(r'\b(calendar|schedule)\b', core.text(a), re.I) or a['href'].startswith('#'):
                continue
            target = core.safe_link(url, a['href'])
            if target.startswith(url) and target.rstrip('/.') != url.rstrip('/.') and target not in links:
                links.append(target)
        for target in links[:2]:
            schedule = BeautifulSoup(core.fetch(target), 'html.parser')
            # A linked calendar may omit its header; retain verified home identity.
            if not any(re.search(r'cse\s*\d{3}', core.text(h), re.I) for h in schedule.select('h1,title,.doc-title')):
                identity = schedule.new_tag('div', attrs={'data-course-identity': ''})
                identity.string = f'{code}, {quarter} {year}'
                schedule.append(identity)
            documents.append((schedule, target))
    # Some home pages omit the term entirely; a same-offering linked calendar
    # can supply it. Never override an explicit conflicting course or quarter.
    verified = []
    for doc, source in documents:
        try:
            verified.append(verify_offering(doc, code, quarter, year))
        except ValueError:
            pass
    if not verified:
        verify_offering(soup, code, quarter, year)
    for doc, source in documents:
        try:
            verify_offering(doc, code, quarter, year)
        except ValueError:
            headings = ' '.join(core.text(h) for h in doc.select('h1,title,.doc-title'))
            explicit = re.search(r'\b(Autumn|Winter|Spring|Summer)\s+(20\d{2})\b', headings, re.I)
            numbers = re.findall(r'\bcse\s*(\d{3}[a-z]?)\b', headings, re.I)
            if (explicit and (explicit[1].lower(), int(explicit[2])) != (quarter.lower(), year)) or (numbers and code[3:].lower() not in [n.lower() for n in numbers]):
                raise ValueError('Linked calendar conflicts with the requested offering.')
            identity = doc.new_tag('div', attrs={'data-course-identity': ''})
            identity.string = verified[0] + f' {quarter} {year}'
            doc.append(identity)
    parsed = [core.parse_course(str(doc), source, code, quarter, year) for doc, source in documents]
    combined = parsed[0]
    for other in parsed[1:]:
        combined['events'].extend(other['events'])
        combined['materials'].extend(other['materials'])
        combined['essentials'].extend(other['essentials'])
        combined['dated_rows'] += other['dated_rows']
    combined['events'] = list({(e['title'], e['date'], e['kind']): e for e in combined['events']}.values())
    combined['materials'] = list({(m['url'], m['date']): m for m in combined['materials']}.values())
    combined['essentials'] = list({e['url']: e for e in combined['essentials']}.values())
    if combined['events']:
        combined['warnings'] = [w for w in combined['warnings'] if not w.startswith('No supported')]
    if code == 'CSE123':
        combined['warnings'].append('Project deadlines use the final dated row of each calendar assignment span. Computer-quiz availability windows are not treated as due dates.')
    # Read a few explicitly linked exam/syllabus pages from this offering only.
    from tracker.exams import enrich
    details = list(documents)
    targets = []
    for doc, source in documents:
        for a in doc.select('a[href]'):
            target = core.safe_link(source, a['href'])
            if re.search(r'\b(midterm|final|exams?|syllabus)\b', core.text(a), re.I) and target.startswith(url) and target not in [u for _, u in details] and target not in targets and not target.lower().split('?')[0].endswith(('.pdf','.zip','.png','.jpg')):
                targets.append(target)
    for target in targets[:3]:
        try:
            details.append((BeautifulSoup(core.fetch(target), 'html.parser'), target))
        except Exception:
            pass  # Optional details cannot discard a successfully imported calendar.
    enrich(combined['events'], details)
    combined['sources'] = [source for _, source in documents]
    return combined
