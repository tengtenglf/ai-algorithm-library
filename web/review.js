(function (root) {
  'use strict';
  const offsets = [1, 7, 30];
  function today() { return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year:'numeric',month:'2-digit',day:'2-digit' }).format(new Date()); }
  function addDays(day, n) { const d = new Date(day + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate()+n); return d.toISOString().slice(0,10); }
  function start(day) { return {start:day, stage:0, last:day}; }
  function dueDate(s) { return s.stage >= offsets.length ? null : addDays(s.start, offsets[s.stage]); }
  function grade(s, remembered, day) { return remembered ? {...s, stage:Math.min(3,s.stage+1), last:day} : start(day); }
  function matches(c, query) { const text=(c.title+' '+c.body).toLocaleLowerCase(); return query.trim().toLocaleLowerCase().split(/\s+/).every(word=>text.includes(word)); }
  function valid(s) { return s && /^\d{4}-\d{2}-\d{2}$/.test(s.start) && Number.isInteger(s.stage) && s.stage>=0 && s.stage<=3 && /^\d{4}-\d{2}-\d{2}$/.test(s.last) && !isNaN(Date.parse(s.start)); }
  const api = {today, addDays, start, dueDate, grade, matches, valid};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Review = api;
})(typeof globalThis==='object'?globalThis:this);
