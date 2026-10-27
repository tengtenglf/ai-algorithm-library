import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('library', ROOT / 'scripts/library.py')
lib = importlib.util.module_from_spec(spec) if spec else None
if spec and spec.loader and (ROOT / 'scripts/library.py').exists():
    spec.loader.exec_module(lib)

# Hand-authored fixture: losing an answer, rewriting text, or accepting a conflicting
# edition must break these tests before damaged content reaches the website.
def lesson(episode=1):
    return (f'# AI 算法寓言\n## 第 {episode} 期｜2026 年 10 月 10 日\n'
            '### 今日主题：测试课程\n\n# 第一课：完整正文\n正文不能被改写。\n\n'
            + '\n\n'.join(f'**Q{i}｜理解题：** 原题{i}？' for i in range(1, 10))
            + '\n\n# 📝 参考答案与深度思考\n\n'
            + '\n\n'.join(f'### Q{i}：原答案{i}\n\n完整推导{i}，不能只留下标题。' for i in range(1, 10))
            + f'\n\n# 今日连接\n课程结束。\n\n**第 {episode} 期完成。**\n')

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(hasattr(lib, 'parse_course'), '需要实现原文导入与校验')

    def test_preserves_exact_original_and_pairs_nine_answers(self):
        raw = lesson()
        course = lib.parse_course(raw, 'message-1', 'conversation-1')
        self.assertEqual(course['body'], raw)
        self.assertEqual(course['episode'], 1)
        self.assertEqual(course['date'], '2026-10-10')
        self.assertEqual(len(course['questions']), 9)
        self.assertIn('完整推导9，不能只留下标题。', course['questions'][8]['answer'])
        self.assertEqual(course['questions'][0]['question'], '**Q1｜理解题：** 原题1？\n\n')

    def test_rejects_missing_answer_and_reference_only(self):
        with self.assertRaises(ValueError):
            lib.parse_course(lesson().replace('### Q9：原答案9', '### 缺失答案'), 'x', 'y')
        with self.assertRaises(ValueError):
            lib.parse_course('::chatgpt-content-reference{index="0"}', 'x', 'y')

    def test_import_is_idempotent_and_conflicts_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(lib.import_messages(root, [{'id':'a', 'text':lesson()}], 'conv'), 1)
            self.assertEqual(lib.import_messages(root, [{'id':'a', 'text':lesson()}], 'conv'), 0)
            original = (root / 'content/courses/001.json').read_bytes()
            with self.assertRaises(ValueError):
                lib.import_messages(root, [{'id':'b', 'text':lesson().replace('正文不能', '冲突不能')}], 'conv')
            self.assertEqual((root / 'content/courses/001.json').read_bytes(), original)

    def test_batch_validation_is_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                lib.import_messages(root, [{'id':'a','text':lesson()}, {'id':'b','text':lesson(2).replace('### Q9：原答案9','### 丢失')}], 'conv')
            self.assertFalse((root / 'content/courses/001.json').exists())

    def test_audit_reports_missing_instead_of_inventing_courses(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            lib.import_messages(root, [{'id':'x','text':lesson(18)}], 'conv')
            audit = lib.audit(root)
            self.assertEqual(audit['complete_count'], 1)
            self.assertEqual(audit['missing_episodes'], list(range(1,18)))
            with self.assertRaises(ValueError):
                lib.audit(root, require_complete=True)

    def test_renderer_hides_answers_and_does_not_execute_raw_html(self):
        course = lib.parse_course(lesson().replace('正文不能', '<script>alert(1)</script>正文不能'), 'x', 'y')
        rendered = lib.render_course(course)
        self.assertEqual(rendered.count('<details class="answer">'), 9)
        self.assertNotIn('<script>alert(1)</script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertNotIn('<details class="answer" open', rendered)

    def test_math_delimiters_survive_markdown_for_browser_rendering(self):
        rendered = lib.render_md(r'概率 \(P(H\mid E)\) 与公式：' + '\n\n' + r'\[x^2+1\]')
        self.assertIn(r'\(P(H\mid E)\)', rendered)
        self.assertIn(r'\[x^2+1\]', rendered)

    def test_historical_header_and_original_closing_formats(self):
        raw=lesson(1).replace('## 第 1 期｜2026 年 10 月 10 日','# AI 算法寓言 · 第 01 期\n**2026 年 10 月 10 日**').replace('### 今日主题','## 今日主题').replace('**第 1 期完成。**','**第一期课程完成。**')
        self.assertEqual(lib.parse_course(raw,'old-1','conv')['episode'],1)
        raw2=lesson(2).replace('**第 2 期完成。**','这就是今天的《AI 算法寓言·专家成长课程》。')
        self.assertEqual(lib.parse_course(raw2,'old-2','conv')['episode'],2)

    def test_render_resolves_only_archived_citation_annotations(self):
        token='\ue200cite\ue202turn-source\ue201'
        rendered=lib.render_md('原始研究'+token, [{'marker':token,'markdown':'[原论文](https://example.org/paper)'}])
        self.assertIn('href="https://example.org/paper"',rendered)
        self.assertNotIn(token,rendered)

    def test_fetch_rejects_unsafe_or_absent_feed(self):
        with self.assertRaises(ValueError):
            lib.fetch_feed('http://127.0.0.1/a')
        with self.assertRaises(ValueError):
            lib.fetch_feed('')

if __name__ == '__main__':
    unittest.main()
