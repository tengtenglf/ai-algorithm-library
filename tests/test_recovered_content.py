"""Regression against recovered original messages, not generated representations."""
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class OriginalRecoveryTests(unittest.TestCase):
    def test_every_recovered_message_is_preserved_byte_for_byte(self):
        source=json.loads((ROOT/'content/sources/recovered-messages.json').read_text())
        self.assertEqual(len(source['messages']),4)
        for message in source['messages']:
            courses=[json.loads(p.read_text()) for p in (ROOT/'content/courses').glob('*.json')]
            actual=[c for c in courses if c['source']['message_id']==message['id']]
            self.assertEqual(len(actual),1)
            self.assertEqual(actual[0]['body'].encode('utf-8'),message['text'].encode('utf-8'))
            self.assertEqual(len(actual[0]['questions']),9)
