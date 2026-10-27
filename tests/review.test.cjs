const test = require('node:test');
const assert = require('node:assert/strict');
let R; try { R = require('../web/review.js'); } catch {}
test('按学习起点安排D+1、D+7、D+30，不把复习误算为已掌握', () => {
  assert.ok(R, '需要实现复习调度');
  let s = R.start('2026-10-27');
  assert.equal(R.dueDate(s), '2026-10-28');
  s = R.grade(s, true, '2026-10-28');
  assert.equal(R.dueDate(s), '2026-11-03');
  s = R.grade(s, true, '2026-11-03');
  assert.equal(R.dueDate(s), '2026-11-26');
  assert.equal(R.dueDate(R.grade(s, true, '2026-11-26')), null);
});
test('忘记会重新排期；搜索覆盖正文、题目和答案', () => {
  assert.ok(R);
  const s = R.grade(R.start('2026-10-10'), false, '2026-10-27');
  assert.equal(R.dueDate(s), '2026-10-28');
  assert.equal(R.matches({title:'并行',body:'正文 原题 原答案 Amdahl'}, 'amdahl 原答案'), true);
  assert.equal(R.matches({title:'并行',body:'原题'}, '不存在'), false);
});
