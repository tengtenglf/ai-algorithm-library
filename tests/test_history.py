import hashlib,json,unittest
from datetime import date,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FullHistoryTests(unittest.TestCase):
    def test_historical_courses_are_exact_joins_of_original_message_fragments(self):
        evidence=json.loads((ROOT/'content/sources/shared-course-fragments.json').read_text())
        fragments={m['id']:m['text'] for m in evidence['fragments']}
        for recipe in evidence['assemblies']:
            if recipe['episode']>14:continue
            body=''.join(fragments[key] for key in recipe['parts'])
            course=json.loads((ROOT/'content/courses'/f"{recipe['episode']:03}.json").read_text())
            self.assertEqual(course['body'].encode(),body.encode())
            self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),recipe['assembled_sha256'])
    def test_all_eighteen_editions_have_original_nine_questions_and_answers(self):
        courses=[json.loads(p.read_text()) for p in sorted((ROOT/'content/courses').glob('*.json'))]
        courses=[c for c in courses if c['episode']<=18]
        self.assertEqual([c['episode'] for c in courses],list(range(1,19)))
        self.assertEqual(sum(len(c['questions']) for c in courses),162)
        for i,c in enumerate(courses):
            self.assertEqual(c['date'],(date(2026,10,10)+timedelta(days=i)).isoformat())
            self.assertEqual([q['id'] for q in c['questions']],list(range(1,10)))
            self.assertTrue(all(q['question'].strip() and q['answer'].strip() for q in c['questions']))
