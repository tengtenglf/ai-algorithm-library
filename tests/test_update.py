import importlib.util,json,tempfile,unittest,sys
import contextlib,io
from unittest.mock import patch
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
    def run_main(self,root,args):
        with patch.object(update,'ROOT',root),patch.object(sys,'argv',['update.py',*args]),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            try:return update.main()
            except SystemExit as error:return error.code
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

    def test_recovery_date_imports_original_without_changing_it_on_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.inbox(root,lesson(18))
            original=source.read_bytes();report=root/'report.json'
            args=['--date','2026-10-10','--report',str(report)]
            self.assertEqual(self.run_main(root,args),0)
            course=root/'content/courses/018.json';saved=course.read_bytes()
            self.assertEqual(json.loads(report.read_text())['target_date'],'2026-10-10')
            self.assertEqual(self.run_main(root,args),0)
            self.assertEqual(json.loads(report.read_text())['imported'],0)
            self.assertEqual(course.read_bytes(),saved)
            self.assertEqual(source.read_bytes(),original)

    def test_missing_daily_source_leaves_failure_evidence_without_changing_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ledger=root/'content/sync/latest.json'
            ledger.parent.mkdir(parents=True);ledger.write_text('{"target_date":"2026-10-09"}')
            original=ledger.read_bytes();report=root/'report.json'
            args=['--date','2026-10-10','--report',str(report)]
            self.assertEqual(self.run_main(root,args),1)
            evidence=json.loads(report.read_text())
            self.assertEqual(evidence['status'],'failed')
            self.assertEqual(evidence['error_code'],'missing_inbox')
            self.assertEqual(evidence['target_date'],'2026-10-10')
            self.assertEqual(ledger.read_bytes(),original)
            self.assertFalse((root/'content/courses').exists())

    def test_inbox_filename_must_match_declared_date(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.inbox(root,lesson(18))
            wrong=source.with_name('2026-10-11.json');source.rename(wrong)
            with self.assertRaises(ValueError):update.sync(root,'2026-10-10',wrong)
            self.assertFalse((root/'content/courses').exists())

    def test_invalid_or_future_recovery_date_writes_failure_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);report=root/'report.json'
            for target in ['not-a-date','2026-02-30','9999-12-31']:
                with self.subTest(target=target):
                    self.assertEqual(self.run_main(root,['--date',target,'--report',str(report)]),1)
                    evidence=json.loads(report.read_text())
                    self.assertEqual(evidence['status'],'failed')
                    self.assertEqual(evidence['error_code'],'invalid_source_or_sync')
            self.assertFalse((root/'content/courses').exists())
            self.assertFalse((root/'content/sync/latest.json').exists())

    def test_invalid_inbox_keeps_original_courses_and_success_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.inbox(root,lesson(18));report=root/'report.json'
            args=['--date','2026-10-10','--report',str(report)]
            self.assertEqual(self.run_main(root,args),0)
            course=root/'content/courses/018.json';original=course.read_bytes()
            ledger=root/'content/sync/latest.json';saved=ledger.read_bytes()
            for raw in ['{invalid JSON',json.dumps({'conversation_id':'conv','messages':[{'id':'real-18','text':lesson(18).replace('### Q9：原答案9','### 缺失答案')}]}),json.dumps({'conversation_id':'conv','messages':[{'id':'real-18','text':lesson(18).replace('正文不能','冲突不能')}]})]:
                with self.subTest(raw=raw[:30]):
                    source.write_text(raw)
                    self.assertEqual(self.run_main(root,args),1)
                    self.assertEqual(json.loads(report.read_text())['status'],'failed')
                    self.assertEqual(course.read_bytes(),original)
                    self.assertEqual(ledger.read_bytes(),saved)

    def test_cloud_delivery_preserves_body_without_inventing_message_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.inbox(root,lesson(19))
            payload=json.loads(source.read_text())
            payload['conversation_id']='6ac9e367-6ea8-83ec-aeee-555083ffcfb7'
            message=payload['messages'][0]
            message['id']=None
            message['delivery']={'automation_id':'6ac9e53a5cdc8191b955c5a84cdc3c2f',
                                 'id':'6ac9e53a5cdc8191b955c5a84cdc3c2f:2026-10-10'}
            source.write_text(json.dumps(payload))
            report=update.sync(root,'2026-10-10',source)
            course=json.loads((root/'content/courses/019.json').read_text())
            self.assertEqual(course['body'],lesson(19))
            self.assertEqual(course['source']['kind'],'verbatim_chatgpt_task_output')
            self.assertIsNone(course['source']['message_id'])
            self.assertEqual(course['source']['delivery'],message['delivery'])
            self.assertEqual(report['source_message_ids'],[None])
            self.assertEqual(report['source_delivery_ids'],[message['delivery']['id']])
            self.assertEqual(update.sync(root,'2026-10-10',source)['imported'],0)
            message['delivery']['id']='6ac9e53a5cdc8191b955c5a84cdc3c2f:2026-10-11'
            source.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):update.sync(root,'2026-10-10',source)

    def test_cloud_delivery_rejects_missing_provenance_and_fabricated_message_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.inbox(root,lesson(19))
            payload=json.loads(source.read_text());payload['messages'][0]['id']=None
            source.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):update.sync(root,'2026-10-10',source)
            payload['messages'][0]['id']='made-up-uuid'
            payload['messages'][0]['delivery']={'automation_id':'6ac9e53a5cdc8191b955c5a84cdc3c2f','id':'6ac9e53a5cdc8191b955c5a84cdc3c2f:2026-10-10'}
            source.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):update.sync(root,'2026-10-10',source)
            self.assertFalse((root/'content/courses').exists())
