import json
from pathlib import Path
import tempfile
import unittest
from tracker import planner
from tracker.store import Store

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'data/planner.json').read_text(encoding='utf-8'))
COURSES = {c['code']: c for c in CATALOG['courses']}
TERM = {'quarter': 'Autumn', 'year': 2026}

def profile(*codes, interests=()):
    return {**planner.default_profile(), 'completed': [{'code': c, 'grade': 3.0} for c in codes], 'interests': list(interests)}

def entry(code, quarter='Winter', year=2027):
    return {'code': code, 'quarter': quarter, 'year': year}

class PlannerTests(unittest.TestCase):
    def test_empty_history_is_not_seeded(self):
        result = planner.build_state(CATALOG, planner.default_profile(), [], [], TERM)
        self.assertEqual(result['profile']['major'], 'cs')
        self.assertEqual(result['profile']['completed'], [])
        self.assertEqual(result['plan'], [])
        self.assertEqual(result['requirements']['fundamentals_done'], 0)
        self.assertTrue(result['suggestions'])

    def test_and_or_groups_and_minimum_grades(self):
        self.assertFalse(planner.prerequisite_status(COURSES['CSE446'], {'CSE332': 3, 'CSE312': 3})['met'])
        self.assertTrue(planner.prerequisite_status(COURSES['CSE446'], {'CSE332': 3, 'CSE312': 3, 'MATH208': 3})['met'])
        self.assertFalse(planner.prerequisite_status(COURSES['CSE311'], {'CSE123': 1.9, 'MATH126': 3})['met'])
        result = planner.prerequisite_status(COURSES['CSE311'], {'CSE143': None, 'MATH135': 3})
        self.assertTrue(result['met'])
        self.assertTrue(result['grade_review'])
        self.assertFalse(planner.prerequisite_status(COURSES['CSE312'], {'CSE311': 0})['met'])

    def test_recommendations_do_not_become_requirements(self):
        self.assertTrue(planner.prerequisite_status(COURSES['CSE447'], {'CSE312': 3, 'CSE332': 3})['met'])
        self.assertIn('CSE446', COURSES['CSE447']['recommended'])
        self.assertFalse(planner.prerequisite_status(COURSES['MATH208'], {})['met'])

    def test_same_quarter_does_not_qualify_but_valid_earlier_chain_does(self):
        p = profile('CSE123', 'MATH126')
        result = planner.build_state(CATALOG, p, [entry('CSE311'), entry('CSE312')], [], TERM)
        self.assertFalse(result['plan'][1]['readiness']['met'])
        self.assertEqual(result['plan'][1]['same_quarter_prerequisites'], ['CSE311'])
        result = planner.build_state(CATALOG, p, [entry('CSE311'), entry('CSE312', 'Spring')], [], TERM)
        self.assertTrue(result['plan'][1]['readiness']['met'])
        self.assertEqual(result['plan'][1]['assumed_prerequisites'], ['CSE311'])
        self.assertEqual(result['plan'][1]['offering_status'], 'unverified')
        broken = planner.build_state(CATALOG, profile(), [entry('CSE311'), entry('CSE312', 'Spring')], [], TERM)
        self.assertFalse(broken['plan'][1]['readiness']['met'])

    def test_current_courses_are_assumed_only_for_later_terms(self):
        imported = [{'code': 'CSE311', **TERM}]
        result = planner.build_state(CATALOG, profile(), [entry('CSE312')], imported, TERM)
        self.assertTrue(result['plan'][0]['readiness']['met'])
        self.assertEqual(result['profile']['completed'], [])
        same = planner.build_state(CATALOG, profile(), [entry('CSE312', **TERM)], imported, TERM)
        self.assertFalse(same['plan'][0]['readiness']['met'])

    def test_requirements_do_not_count_fundamentals_as_core_or_failed_credits(self):
        p = profile('CSE123', 'CSE311', 'CSE312', 'CSE331', 'CSE332', 'CSE351', 'CSE333', 'CSE480')
        r = planner.requirement_progress(CATALOG, p)
        self.assertEqual(r['fundamentals_done'], 6)
        self.assertEqual(r['core_done'], 1)
        self.assertEqual(r['elective_credits'], COURSES['CSE333']['credits'])
        self.assertIn('CSE480', r['variable_credit_review'])
        p['completed'] = [{'code': 'CSE333', 'grade': 0}]
        self.assertEqual(planner.requirement_progress(CATALOG, p)['elective_credits'], 0)

    def test_suggestions_explain_interests_and_exclude_owned_courses(self):
        p = profile('CSE123', 'CSE311', 'CSE312', 'CSE332', 'MATH208', interests=['ai'])
        result = planner.build_state(CATALOG, p, [entry('CSE446')], [{'code':'CSE351', **TERM}], TERM)
        codes = {s['code'] for s in result['suggestions']}
        self.assertFalse(codes.intersection({'CSE123', 'CSE311', 'CSE312', 'CSE332', 'CSE351', 'CSE446'}))
        self.assertTrue(any(any('Matches' in reason for reason in s['reasons']) for s in result['suggestions']))

    def test_validation_and_source_coverage(self):
        with self.assertRaises(ValueError): planner.normalize_plan([entry('CSE311'), entry('CSE311','Spring')], CATALOG)
        with self.assertRaises(ValueError): planner.normalize_profile(profile('CSE999'), CATALOG)
        with self.assertRaises(ValueError): planner.normalize_profile({**profile(), 'completed':[{'code':'CSE123','grade':4.5}]}, CATALOG)
        for course in CATALOG['courses']:
            self.assertTrue(course['source'].startswith('https://'))
            for group in course['prerequisites']:
                self.assertTrue(set(group['any_of']).issubset(COURSES))

    def test_backup_roundtrip_and_invalid_restore_is_atomic(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.local-data' / 'tests') as directory:
            store = Store(directory)
            store.save_planner(profile('CSE123'), [entry('CSE311')])
            backup = store.export()
            store.save_planner(profile(), [])
            store.restore(backup)
            self.assertEqual(store.export()['planner'], backup['planner'])
            store.restore({'version':1, 'courses':[]})
            self.assertEqual(store.export()['planner'], backup['planner'])
            bad = {**backup, 'planner': {'profile':profile('CSE999'), 'plan':[]}}
            with self.assertRaises(ValueError): store.restore(bad)
            self.assertEqual(store.export()['planner'], backup['planner'])

