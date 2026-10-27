import importlib.util,json,tempfile,unittest,sys
from pathlib import Path
from test_library import lesson
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
p=ROOT/'scripts/update.py'
spec=importlib.util.spec_from_file_location('update',p)
update=importlib.util.module_from_spec(spec)
if p.exists(): spec.loader.exec_module(update)

class UpdateTests(unittest.TestCase):
    def setUp(self): self.assertTrue(hasattr(update,'sync'),'需要实现真实原文入库的自动更新入口')
    def inbox(self,root,raw):
        source=root/'content/inbox/2026-10-10.json';source.parent.mkdir(parents=True)
        source.write_text(json.dumps({'conversation_id':'conv','messages':[{'id':'real-18','text':raw}]}))
        return source
    def test_real_course_import_and_idempotent_second_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.inbox(root,lesson(18))
            first=update.sync(root,'2026-10-10',source)
            self.assertEqual(first['imported'],1)
            self.assertEqual(first['source_episodes'],[18])
            self.assertEqual(first['complete_count'],1)
            self.assertEqual(first['source_message_ids'],['real-18'])
            second=update.sync(root,'2026-10-10',source)
            self.assertEqual(second['imported'],0)
            self.assertEqual(second['complete_count'],1)
    def test_stale_or_incomplete_source_never_changes_courses(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.inbox(root,lesson(18))
            with self.assertRaises(ValueError):update.sync(root,'2026-10-11',source)
            self.assertFalse((root/'content/courses').exists())
            source.write_text(json.dumps({'conversation_id':'conv','messages':[{'id':'x','text':lesson(18).replace('### Q9：原答案9','### 丢失')}]}))
            with self.assertRaises(ValueError):update.sync(root,'2026-10-10',source)
            self.assertFalse((root/'content/courses').exists())
    def test_refuses_source_outside_inbox(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(ValueError):update.sync(root,'2026-10-10',root/'README.md')
