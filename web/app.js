'use strict';
(async function () {
  const R=window.Review, prefix=document.body.dataset.prefix || './', key='ai-algorithm-library-progress-v1';
  const el=(tag,text,cls)=>{ const x=document.createElement(tag); if(text!==undefined)x.textContent=text; if(cls)x.className=cls; return x; };
  let courses;
  try { const response=await fetch(prefix+'data.json'); if(!response.ok)throw new Error('课程数据加载失败'); courses=await response.json(); }
  catch(error) { const p=el('p','课程数据暂时无法加载。课程原文链接仍可直接打开。','notice'); document.querySelector('main').prepend(p); return; }
  const allowed=new Set(courses.map(c=>String(c.episode)));
  function read() { const value=JSON.parse(localStorage.getItem(key)||'{}'); if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('进度格式错误'); return value; }
  function save(value) { localStorage.setItem(key,JSON.stringify(value)); }
  const search=document.querySelector('#search');
  if(search) {
    function apply() { const q=search.value; let count=0; for(const c of courses){const card=document.querySelector(`[data-episode="${c.episode}"]`);const show=R.matches(c,q);if(card)card.hidden=!show;if(show)count++;} document.querySelector('#search-status').textContent=q?`找到 ${count} 期匹配课程`:`共 ${courses.length} 期原文 · 按期数倒序`;document.querySelector('#empty').hidden=count!==0; }
    search.addEventListener('input',apply); apply();
  }
  const syncStatus=document.querySelector('#sync-status');
  if(syncStatus){try{const response=await fetch(prefix+'sync.json');if(!response.ok)throw new Error('missing');const s=await response.json();syncStatus.textContent=`${s.checked_at} · 处理原始消息${s.processed}条，新增${s.imported}期；原文覆盖${s.complete_count}/${s.expected_count}期。部署结果请结合Actions记录核验。`;}catch{syncStatus.textContent='尚未取得自动入库记录；不能据此声称闭环成功。';}}
  const learn=document.querySelector('[data-learn]');
  if(learn) {
    learn.addEventListener('click',()=>{try {const s=read(), id=learn.dataset.learn;if(!s[id])s[id]=R.start(R.today());save(s);document.querySelector('#learn-status').textContent=`已加入复习；下次：${R.dueDate(s[id]) || '本轮已完成'}。`; }catch{document.querySelector('#learn-status').textContent='浏览器未能保存进度，请检查本地存储权限。';}});
    document.querySelector('#toggle-answers').addEventListener('click',event=>{ const list=[...document.querySelectorAll('details.answer')];const opening=list.some(x=>!x.open);for(const x of list)x.open=opening;event.target.textContent=opening?'收起全部答案':'展开全部答案'; });
  }
  const list=document.querySelector('#review-list');
  if(list) {
    function render() {
      list.replaceChildren(); let state;try{state=read();}catch{list.append(el('p','无法读取浏览器进度，请检查本地存储权限。'));return;}
      const learned=courses.filter(c=>R.valid(state[c.episode]));
      if(!learned.length){list.append(el('p','还没有加入复习的课程。阅读课程后，点击“读完了，加入复习”。','empty-state'));return;}
      const due=learned.filter(c=>{const day=R.dueDate(state[c.episode]);return day && day<=R.today();});
      const other=learned.filter(c=>!due.includes(c));
      list.append(el('h2',`今日到期 ${due.length} 期`));
      for(const c of [...due,...other]) {
        const s=state[c.episode], day=R.dueDate(s), card=el('section',undefined,'review-card');
        const link=el('a',`第${c.episode}期 · ${c.title}`);link.href=`${prefix}courses/${String(c.episode).padStart(3,'0')}.html`;card.append(link);
        card.append(el('p',day?`${day<=R.today()?'待复习':'下次复习'}：${day} · D+${[1,7,30][s.stage]}`:'D+1 / D+7 / D+30 本轮均已完成','muted'));
        if(due.includes(c)) {
          for(const q of c.questions) {const block=el('div',undefined,'review-question');block.append(el('p',q.question));const details=el('details',undefined,'answer');details.append(el('summary',`Q${q.id} 原答案`),el('div',q.answer,'verbatim-answer'));block.append(details);card.append(block);}
          const actions=el('div',undefined,'actions');for(const [label,remembered] of [['已掌握，安排下一次',true],['仍模糊，明天再练',false]]){const b=el('button',label);b.addEventListener('click',()=>{try{const current=read();current[c.episode]=R.grade(current[c.episode],remembered,R.today());save(current);render();}catch{document.querySelector('#progress-status').textContent='保存失败，请检查浏览器本地存储权限。';}});actions.append(b);}card.append(actions);
        }
        list.append(card);
      }
    }
    render();
    document.querySelector('#export-progress').addEventListener('click',()=>{try{const blob=new Blob([JSON.stringify({schema_version:1,progress:read()},null,2)],{type:'application/json'});const a=el('a');a.href=URL.createObjectURL(blob);a.download=`algorithm-review-${R.today()}.json`;a.click();URL.revokeObjectURL(a.href);}catch{document.querySelector('#progress-status').textContent='导出失败。';}});
    document.querySelector('#import-progress').addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file||file.size>1000000)throw new Error('请选择1MB以内的JSON进度文件');const value=JSON.parse(await file.text());if(value.schema_version!==1||!value.progress||typeof value.progress!=='object'||Array.isArray(value.progress))throw new Error('进度文件格式不正确');const entries=Object.entries(value.progress);if(entries.some(([id,s])=>!allowed.has(id)||!R.valid(s)))throw new Error('进度含未知课程或无效日期');save({...read(),...value.progress});document.querySelector('#progress-status').textContent='进度已导入。';render();}catch(error){document.querySelector('#progress-status').textContent=error.message;}event.target.value='';});
  }
})();
