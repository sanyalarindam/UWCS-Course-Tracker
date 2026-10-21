import unittest
from bs4 import BeautifulSoup
from tracker.exams import enrich, logistics

class ExamDetailsTests(unittest.TestCase):
    def test_explicit_time_ranges_and_rooms(self):
        self.assertEqual(logistics('Midterm 1: 6:30–8:20 pm PDT; Location: KNE 110'), {'time':'6:30–8:20 pm PDT','location':'KNE 110'})
        self.assertEqual(logistics('Final exam at 2pm in GUG 220')['location'], 'GUG 220')
        self.assertEqual(logistics('Midterm CSE 312 October 21')['location'], None)

    def test_exam_specific_heading_and_source(self):
        events = [{'kind':'exam','title':'Midterm','time':None}, {'kind':'exam','title':'Final exam','time':None}]
        page = BeautifulSoup('<h2>Midterm</h2><p>Time: 6:30–8:20 pm; Location: KNE 110</p><h2>Final exam</h2><p>Time: 9:00–11:00 am; Location: GUG 220</p>', 'html.parser')
        enrich(events, [(page, 'https://courses.cs.washington.edu/exams/')])
        self.assertEqual(events[0]['location'], 'KNE 110')
        self.assertEqual(events[1]['location'], 'GUG 220')
        self.assertEqual(events[0]['time'], '6:30–8:20 pm')
        self.assertTrue(events[0]['exam_details_sources'])

    def test_conflicting_or_unrelated_logistics_not_invented(self):
        event = {'kind':'exam','title':'Midterm','time':None}
        page = BeautifulSoup('<p>Lectures: 10:00 am in CSE 305</p><p>Midterm location: KNE 110</p><p>Midterm location: GUG 220</p>', 'html.parser')
        enrich([event], [(page, 'source')])
        self.assertIsNone(event['time'])
        self.assertNotIn('location', event)

    def test_numbered_exams_and_existing_values_preserved(self):
        events = [{'kind':'exam','title':'Midterm 1','time':'7:00 pm','location':'BAG 131'}, {'kind':'assignment','title':'Midterm homework','time':None}]
        page = BeautifulSoup('<p>Midterm 2: 8:00 pm; Location: KNE 110</p><p>Midterm 1: 6:30 pm; Location: GUG 220</p>', 'html.parser')
        enrich(events, [(page, 'source')])
        self.assertEqual(events[0]['time'], '7:00 pm')
        self.assertEqual(events[0]['location'], 'BAG 131')
        self.assertIsNone(events[1]['time'])
