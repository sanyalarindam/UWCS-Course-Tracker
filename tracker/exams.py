"""Explicit exam logistics from bounded, exam-specific page text."""
import re
from bs4 import BeautifulSoup

TIME = re.compile(r'\b(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s*(?:[ap]\.?m\.?)?(?:\s*(?:[-–—]|to)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s*(?:[ap]\.?m\.?)?)?\s*(?:PT|PST|PDT)?\b', re.I)

def logistics(value):
    time = next((m[0].strip() for m in TIME.finditer(value) if re.search(r':|[ap]\.?m', m[0], re.I)), None)
    location = re.search(r'\b(?:location|room|venue)\s*:\s*([^;\n]+)', value, re.I)
    if not location:
        location = re.search(r'\b(?:in|at)\s+([A-Z]{2,5}\s*\d{2,4}[A-Z]?|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:Hall|Building)\s*\d{0,4})\b', value)
    if not location:
        location = re.search(r'\b([A-Z]{2,5}\s+\d{2,4}[A-Z]?)\b', value)
    place = location[1].strip() if location else None
    if place:
        place = re.split(r'\s+(?:Time|Date|Duration)\s*:', place, flags=re.I)[0].strip(' ,.')
        place = re.sub(r'\s+(?:from\s+)?\d{1,2}:\d{2}.*$', '', place).strip(' ,.')
        if re.match(r'^(?:CSE|MATH|STAT|PHYS|CHEM|BIOL)\s*\d', place): place = None
    return {'time': time, 'location': place}


def exam_key(value):
    match = re.search(r'\b(midterm|final(?:\s+exam)?|exam|quiz)\s*(?:exam\s*)?(\d+)?\b', value, re.I)
    return (('final' if match[1].lower().startswith('final') else match[1].lower()), match[2]) if match else None


def enrich(events, documents):
    for soup, url in documents:
        candidates = []
        for node in soup.select('p, li, tr, .exam, .topic, .class-data'):
            value = node.get_text(' ', strip=True)
            if len(value) <= 900 and exam_key(value): candidates.append(value)
        for heading in soup.select('h1,h2,h3,h4,h5'):
            if not exam_key(heading.get_text(' ', strip=True)): continue
            parts = [heading.get_text(' ', strip=True)]
            for sibling in heading.next_siblings:
                if getattr(sibling, 'name', None) in ('h1','h2','h3','h4','h5'): break
                parts.append(sibling.get_text(' ', strip=True) if hasattr(sibling,'get_text') else str(sibling).strip())
                if sum(map(len, parts)) > 900: break
            if sum(map(len, parts)) <= 900: candidates.append(' '.join(parts))
        for event in events:
            if event['kind'] != 'exam': continue
            key = exam_key(event['title'])
            if not key: continue
            matches = [logistics(value) for value in candidates if exam_key(value) == key and len(re.findall(r'\b(?:midterm|final exam)\b', value, re.I)) <= 1]
            for field in ('time','location'):
                values = {m[field] for m in matches if m[field]}
                if not event.get(field) and len(values) == 1:
                    event[field] = values.pop()
                    event.setdefault('exam_details_sources', []).append(url)
            event['exam_details_sources'] = list(dict.fromkeys(event.get('exam_details_sources', [])))
    return events
