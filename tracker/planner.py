"""Local, explainable course planning. This is not a registration/degree audit."""
import re

QUARTERS = ['Winter', 'Spring', 'Summer', 'Autumn']


def default_profile():
    return {'major': 'cs', 'completed': [], 'interests': [], 'other_elective_credits': 0, 'science_credits': 0, 'capstone_confirmed': False}


def term_index(quarter, year):
    if quarter not in QUARTERS or isinstance(year, bool) or not 2000 <= int(year) <= 2100:
        raise ValueError('Choose a valid quarter and year.')
    return int(year) * 4 + QUARTERS.index(quarter)


def normalize_profile(raw, catalog):
    if not isinstance(raw, dict):
        raise ValueError('Invalid planner profile.')
    profile = default_profile()
    profile['major'] = raw.get('major', 'cs')
    if profile['major'] not in ('cs', 'explore'):
        raise ValueError('Choose Computer Science BS or exploration mode.')
    known = {c['code'] for c in catalog['courses']}
    interests = {i['id'] for i in catalog['interests']}
    choices = raw.get('interests', [])
    if not isinstance(choices, list) or not all(i in interests for i in choices):
        raise ValueError('Choose interests from the planner list.')
    profile['interests'] = list(dict.fromkeys(choices))
    completed = raw.get('completed', [])
    if not isinstance(completed, list) or len(completed) > 200:
        raise ValueError('Invalid completed course history.')
    records = {}
    for record in completed:
        if not isinstance(record, dict):
            raise ValueError('Invalid completed course record.')
        code = re.sub(r'\s+', '', str(record.get('code', ''))).upper()
        if code not in known:
            raise ValueError('Choose a course from this planner catalog. Other approved credits can be recorded separately.')
        grade = record.get('grade')
        if grade is not None:
            if isinstance(grade, bool) or not isinstance(grade, (int, float)) or not 0 <= grade <= 4:
                raise ValueError('Grades must be between 0.0 and 4.0, or left blank.')
            grade = float(grade)
        records[code] = {'code': code, 'grade': grade}
    profile['completed'] = list(records.values())
    for key in ('other_elective_credits', 'science_credits'):
        number = raw.get(key, 0)
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not 0 <= number <= 150:
            raise ValueError('Credit totals must be between 0 and 150.')
        profile[key] = number
    profile['capstone_confirmed'] = bool(raw.get('capstone_confirmed', False))
    return profile


def normalize_plan(raw, catalog):
    known = {c['code'] for c in catalog['courses']}
    if not isinstance(raw, list) or len(raw) > 150:
        raise ValueError('Invalid future course plan.')
    entries = {}
    for entry in raw:
        if not isinstance(entry, dict) or entry.get('code') not in known:
            raise ValueError('Choose a course from the planning catalog.')
        term_index(entry.get('quarter'), entry.get('year', 0))
        code = entry['code']
        if code in entries:
            raise ValueError('A course can be planned only once. Remove it before moving it to another quarter.')
        entries[code] = {'code': code, 'quarter': entry['quarter'], 'year': int(entry['year'])}
    return sorted(entries.values(), key=lambda e: (term_index(e['quarter'], e['year']), e['code']))


def prerequisite_status(course, completed):
    missing, grade_review = [], []
    for group in course['prerequisites']:
        alternatives = [c for c in group['any_of'] if c in completed]
        minimum = group.get('minimum_grade')
        qualifying = [c for c in alternatives if completed[c] is None or completed[c] > 0 and (minimum is None or completed[c] >= minimum)]
        if not qualifying:
            missing.append(group['any_of'])
        elif minimum is not None and not any(completed[c] is not None and completed[c] >= minimum for c in qualifying):
            grade_review.append({'any_of': qualifying, 'minimum_grade': minimum})
    modeled = course.get('modeled', not course.get('external', False))
    return {'met': not missing and modeled, 'missing': missing, 'grade_review': grade_review, 'needs_catalog_review': not modeled}


def requirement_progress(catalog, profile):
    completed = {r['code']: r['grade'] for r in profile['completed']}
    codes = {code for code, grade in completed.items() if grade is None or grade > 0}
    grade_qualified = {c for c, grade in completed.items() if grade is None or grade >= 2.0}
    fundamentals = [{'any_of': group, 'done': bool(grade_qualified.intersection(group))} for group in catalog['fundamentals']]
    core = [c for c in catalog['courses'] if c['core'] and c['code'] in codes]
    upper = [c for c in core if c['code'].startswith('CSE4')]
    fundamental_codes = {c for group in catalog['fundamentals'] for c in group}
    elective = [c for c in catalog['courses'] if c['code'] in codes and c['code'] not in fundamental_codes and (c['core'] or c['code'].startswith('CSE4'))]
    credits = sum(c['credits'] or 0 for c in elective) + profile['other_elective_credits']
    routes = [{'courses': route, 'done': sum(code in grade_qualified for code in route)} for route in catalog['math_routes']]
    science_options = [option for option in catalog.get('science_options', []) if set(option['all_of']).issubset(codes)]
    science_from_courses = min(5, sum(option['credits'] for option in science_options))
    return {'fundamentals': fundamentals, 'fundamentals_done': sum(g['done'] for g in fundamentals),
            'core_done': len(core), 'upper_core_done': len(upper), 'elective_credits': credits,
            'extra_core_or_capstone_done': len(core) >= 7 or profile['capstone_confirmed'],
            'science_credits': min(5, science_from_courses + profile['science_credits']), 'science_course_credits': science_from_courses, 'science_courses': sorted({code for option in science_options for code in option['all_of']}), 'math_routes': routes,
            'grade_review': [r['code'] for r in profile['completed'] if r['grade'] is None],
            'variable_credit_review': [c['code'] for c in elective if c['credits'] is None]}


def build_state(catalog, profile, plan, imported, current_term):
    profile = normalize_profile(profile, catalog)
    plan = normalize_plan(plan, catalog)
    completed = {r['code']: r['grade'] for r in profile['completed']}
    current = {c['code'] for c in imported if current_term and c['quarter'] == current_term['quarter'] and c['year'] == current_term['year']}
    planned = {p['code']: p for p in plan}
    by_code = {c['code']: c for c in catalog['courses']}
    fundamentals = {c for group in catalog['fundamentals'] for c in group}
    progress = requirement_progress(catalog, profile)
    # Course discovery is for future quarters. Current enrollments are provisional,
    # never added to completed history or degree progress.
    future_completed = dict(completed)
    for code in current: future_completed.setdefault(code, None)
    courses, suggestions = [], []
    for course in catalog['courses']:
        code = course['code']
        status = prerequisite_status(course, future_completed)
        required_codes = {code for group in course["prerequisites"] for code in group["any_of"]}
        status["assumed_current"] = sorted((current - set(completed)).intersection(required_codes))
        unlocks = [c['code'] for c in catalog['courses'] if any(code in group['any_of'] for group in c['prerequisites'])]
        record = {**course, 'readiness': status, 'unlocks': unlocks,
                  'status': 'completed' if code in completed else 'current' if code in current else 'planned' if code in planned else 'ready' if status['met'] else 'review' if status['needs_catalog_review'] else 'blocked'}
        courses.append(record)
        if code in completed or code in current or code in planned or course.get('external'):
            continue
        matching = sorted(set(profile['interests']).intersection(course['tags']))
        reasons, score = [], 0
        if profile['major'] == 'cs' and code in fundamentals:
            reasons.append('Remaining CS fundamental'); score += 100
        if profile['major'] == 'cs' and course['core'] and (progress['core_done'] < 7 or progress['upper_core_done'] < 4):
            reasons.append('Counts toward CS core options'); score += 35
        if matching:
            labels = {i['id']: i['label'] for i in catalog['interests']}
            reasons.append('Matches ' + ', '.join(labels[i] for i in matching)); score += 25 * len(matching)
        if unlocks:
            reasons.append(f'Prerequisite for {len(unlocks)} mapped courses'); score += min(len(unlocks), 10) * 2
        if status['met']: score += 50
        if not reasons or not course.get('modeled', True): continue
        suggestions.append({'code': code, 'score': score, 'reasons': reasons, 'readiness': status})
    # Do not suggest an alternative to a satisfied fundamental or an earlier intro course.
    satisfied_alternatives = {code for group in catalog['fundamentals'] if any(code in completed and (completed[code] is None or completed[code] >= 2) for code in group) for code in group}
    earlier_intro = {'CSE121', 'CSE122', 'CSE142'} if {'CSE123', 'CSE143'}.intersection(completed) else {'CSE121'} if 'CSE122' in completed else set()
    suggestions = [s for s in suggestions if s['code'] not in satisfied_alternatives | earlier_intro]
    suggestions.sort(key=lambda s: (not s['readiness']['met'], -s['score'], s['code']))
    evaluated_plan = []
    evaluated_by_code = {}
    for entry in plan:
        before = dict(completed)
        earlier = [p for p in plan if term_index(p['quarter'], p['year']) < term_index(entry['quarter'], entry['year']) and evaluated_by_code.get(p['code'], {}).get('readiness', {}).get('met')]
        assumed = [p['code'] for p in earlier]
        if current_term and term_index(current_term['quarter'], current_term['year']) < term_index(entry['quarter'], entry['year']):
            assumed += sorted(current - set(completed))
        for code in assumed: before.setdefault(code, None)
        readiness = prerequisite_status(by_code[entry['code']], before)
        prerequisites = {c for group in by_code[entry['code']]['prerequisites'] for c in group['any_of']}
        same_term = [p['code'] for p in plan if p['code'] in prerequisites and p['quarter'] == entry['quarter'] and p['year'] == entry['year'] and p['code'] not in completed]
        evaluated = {**entry, 'readiness': readiness, 'assumed_prerequisites': sorted(set(assumed).intersection(prerequisites)), 'same_quarter_prerequisites': same_term, 'offering_status': 'unverified'}
        evaluated_plan.append(evaluated)
        evaluated_by_code[entry['code']] = evaluated
    return {'version': catalog['version'], 'sources': catalog['sources'], 'interests': catalog['interests'], 'courses': courses,
            'current_courses': sorted(current - set(completed)), 'profile': profile, 'plan': evaluated_plan, 'requirements': progress, 'suggestions': suggestions[:12]}
