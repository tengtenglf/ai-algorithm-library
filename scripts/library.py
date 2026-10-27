#!/usr/bin/env python3
"""Import verbatim source messages, validate question/answer pairs, build static HTML."""
import argparse
import hashlib
import html
import ipaddress
import json
import os
import re
import shutil
import socket
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
MD = MarkdownIt('commonmark', {'html': False}).enable('table')


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def parse_course(raw, message_id, conversation_id):
    ep = re.search(r'^#{1,3}\s+第\s*(\d+)\s*期[｜|]', raw, re.M)
    day = re.search(r'(20\d\d)\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', raw)
    title = re.search(r'^###\s*今日主题[：:]\s*(.+)', raw, re.M)
    section = re.search(r'^# [^\n]*参考答案[^\n]*\n', raw, re.M)
    if not all([ep, day, title, section]) or len(raw) < 500:
        raise ValueError('不是完整课程：期号、日期、主题、正文或原答案缺失；禁止用内容引用或摘要代替')
    episode = int(ep.group(1))
    if not 1 <= episode <= 99999:
        raise ValueError('期号超出范围')
    when = date(*map(int, day.groups())).isoformat()
    if not re.search(r'第\s*' + str(episode) + r'\s*期[^\n]{0,4}完成', raw[-700:]):
        raise ValueError('课程结束标记缺失，可能被截断')
    before, after = raw[:section.start()], raw[section.end():]
    qm = list(re.finditer(r'^\*\*Q(\d+)[｜|：:][^\n]*\n', before, re.M))
    am = list(re.finditer(r'^###\s+Q(\d+)[：:][^\n]*\n', after, re.M))
    qids, aids = [int(x.group(1)) for x in qm], [int(x.group(1)) for x in am]
    if qids != list(range(1, 10)) or aids != qids:
        raise ValueError(f'原题/原答案必须完整一一对应Q1—Q9，收到 {qids}/{aids}')
    pairs = []
    for i, (q, a) in enumerate(zip(qm, am)):
        qend = qm[i + 1].start() if i + 1 < len(qm) else len(before)
        question = before[q.start():qend]
        # Questions finish at the next lesson/section heading, not the next Q.
        boundary = re.search(r'^#{1,3}\s+', question, re.M)
        if boundary:
            question = question[:boundary.start()]
        aend = am[i + 1].start() if i + 1 < len(am) else len(after)
        answer = after[a.start():aend]
        boundary = re.search(r'^#{1,2}\s+', answer, re.M)
        if boundary:
            answer = answer[:boundary.start()]
        if len(answer.split('\n', 1)[-1].strip()) < 8:
            raise ValueError(f'Q{i+1}原答案只有标题或不完整')
        pairs.append({'id': i+1, 'question': question, 'answer': answer})
    return {'schema_version': 1, 'episode': episode, 'date': when, 'title': title.group(1),
            'body': raw, 'body_sha256': sha(raw), 'questions': pairs,
            'source': {'kind': 'verbatim_chatgpt_message', 'conversation_id': conversation_id,
                       'message_id': message_id, 'retrieved_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}}


def import_messages(root, messages, conversation_id):
    folder = root / 'content/courses'
    pending = {}
    for message in messages:
        raw = message.get('text', '')
        if not re.search(r'第\s*\d+\s*期[｜|]', raw):
            continue
        course = parse_course(raw, message['id'], conversation_id)
        path = folder / f'{course["episode"]:03}.json'
        if path in pending and pending[path]['body_sha256'] != course['body_sha256']:
            raise ValueError(f'批内同一期内容冲突：{path.name}')
        if path.exists():
            old = json.loads(path.read_text(encoding='utf-8'))
            if old['body_sha256'] != course['body_sha256']:
                raise ValueError(f'同一期原文冲突：{path.name}；请人工审核后通过Git变更，禁止自动覆盖')
            continue
        pending[path] = course
    # Validate the entire batch before writing any course.
    if pending:
        folder.mkdir(parents=True, exist_ok=True)
    for path, course in pending.items():
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(course, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temp.replace(path)
    return len(pending)


def messages_from_payload(payload):
    if isinstance(payload, dict) and 'structuredContent' in payload and payload['structuredContent']:
        payload = payload['structuredContent']
    if isinstance(payload, dict) and 'content' in payload and not 'turns' in payload:
        texts = [x['text'] for x in payload['content'] if x.get('type') == 'text']
        if texts:
            payload = json.loads(texts[0])
    if not isinstance(payload, dict):
        raise ValueError('输入必须是包含messages或read_thread结果的JSON对象')
    if 'turns' in payload:
        return ([i for t in payload['turns'] for i in t['items'] if i.get('type') == 'agentMessage'],
                payload.get('thread', {}).get('id', 'unknown'))
    if not isinstance(payload.get('messages'), list) or not payload.get('conversation_id'):
        raise ValueError('Feed需要conversation_id与messages数组')
    return payload['messages'], payload['conversation_id']


def load_courses(root):
    courses = []
    for path in sorted((root / 'content/courses').glob('*.json')):
        course = json.loads(path.read_text(encoding='utf-8'))
        fresh = parse_course(course['body'], course['source']['message_id'], course['source']['conversation_id'])
        for key in ['episode', 'date', 'title', 'body_sha256', 'questions']:
            if fresh[key] != course[key]:
                raise ValueError(f'原文与派生字段不一致：{path.name}/{key}')
        if path.stem != f'{course["episode"]:03}':
            raise ValueError(f'文件名与期号不一致：{path}')
        courses.append(course)
    return courses


def audit(root, require_complete=False):
    courses = load_courses(root)
    ids = [x['episode'] for x in courses]
    expected = max([18] + ids)
    missing = sorted(set(range(1, expected + 1)) - set(ids))
    result = {'expected_count': expected, 'complete_count': len(courses),
              'episodes': ids, 'missing_episodes': missing,
              'question_count': sum(len(x['questions']) for x in courses),
              'answer_count': sum(len(x['questions']) for x in courses),
              'unresolved_citations': sum(len(re.findall(r':chatgpt-content-reference\{', x['body'])) for x in courses),
              'chatgpt_task_output_bridge': 'not_verified',
              'source_project_recovered': False}
    if require_complete and missing:
        raise ValueError(f'完整性验收未通过：缺少第 {missing} 期')
    return result


def render_md(text):
    # Citation IDs have no public URL; show the evidence gap without inventing links.
    text = re.sub(r'::?chatgpt-content-reference\{[^}]*\}', '〔原聊天引用：未解析，待补来源〕', text)
    math = []
    def protect(match):
        token = f'ALGORITHMMATH{len(math)}TOKEN'
        math.append(html.escape(match.group()))
        return token
    text = re.sub(r'\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)', protect, text)
    rendered = MD.render(text)
    for i, value in enumerate(math):
        rendered = rendered.replace(f'ALGORITHMMATH{i}TOKEN', value)
    return rendered


def render_course(course):
    raw = course['body']
    section = re.search(r'^# [^\n]*参考答案[^\n]*\n', raw, re.M)
    before, after = raw[:section.end()], raw[section.end():]
    matches = list(re.finditer(r'^###\s+Q(\d+)[：:][^\n]*\n', after, re.M))
    chunks, cursor = [render_md(before)], 0
    for i, match in enumerate(matches):
        answer = course['questions'][i]['answer']
        start, end = match.start(), match.start() + len(answer)
        chunks.append(render_md(after[cursor:start]))
        label = match.group().strip().lstrip('#').strip()
        chunks.append('<details class="answer"><summary>' + html.escape(label) + '</summary>'
                      + render_md(answer.split('\n', 1)[-1]) + '</details>')
        cursor = end
    chunks.append(render_md(after[cursor:]))
    return ''.join(chunks)


def page(title, content, prefix='./', extra=''):
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · AI 算法寓言</title><meta name="description" content="课程原文、原题原答案与间隔复习">
<link rel="stylesheet" href="{prefix}style.css"><link rel="stylesheet" href="{prefix}vendor/katex.min.css"><script defer src="{prefix}vendor/katex.min.js"></script><script defer src="{prefix}vendor/auto-render.min.js"></script><script defer src="{prefix}math.js"></script><script defer src="{prefix}review.js"></script><script defer src="{prefix}app.js"></script></head>
<body data-prefix="{prefix}" {extra}><header><a class="brand" href="{prefix}index.html"><span class="brand-icon">言</span>AI 算法寓言<span class="edition">学习书架</span></a>
<nav aria-label="主导航"><a href="{prefix}index.html">课程目录</a><a href="{prefix}review.html">间隔复习</a><a href="{prefix}status.html">内容与更新状态</a></nav></header>
{content}<footer><p>先回忆，再看答案。把一个知识点，变成自己的判断。</p><a href="{prefix}status.html">查看原文覆盖与更新证据</a></footer></body></html>'''


def build(root):
    courses, report = load_courses(root), audit(root)
    out = root / 'dist'
    out.mkdir(exist_ok=True)
    for sub in ['courses', 'originals']:
        if (out / sub).exists():
            shutil.rmtree(out / sub)
        (out / sub).mkdir()
    for name in ['style.css', 'app.js', 'review.js', 'math.js']:
        shutil.copy2(root / 'web' / name, out / name)
    shutil.copytree(root / 'web/vendor', out / 'vendor', dirs_exist_ok=True)
    (out / '.nojekyll').write_text('')
    cards = []
    for c in reversed(courses):
        ep = c['episode']
        cards.append(f'<a class="course-card" data-episode="{ep}" href="./courses/{ep:03}.html"><div class="card-meta"><span>第 {ep:02} 期</span><time>{c["date"]}</time></div><h3>{html.escape(c["title"])}</h3><p>原文完整保留 · 3堂课 · 9道原题与原答案</p><span class="card-arrow">开始阅读 ↗</span></a>')
        headings = [(i, x) for i, x in enumerate(re.findall(r'^#{1,2}\s+(.+)$', c['body'], re.M))]
        article = render_course(c)
        counter = iter(range(len(headings)))
        article = re.sub(r'<h([12])>', lambda m:f'<h{m[1]} id="section-{next(counter)}">', article)
        toc = ''.join(f'<a href="#section-{i}">{html.escape(x)}</a>' for i,x in headings)
        content = f'''<main class="reading"><aside class="toc"><a href="../index.html">← 返回书架</a><p class="eyebrow">本期目录</p>{toc}</aside><div class="reading-main"><div class="reading-intro"><span class="eyebrow">第 {ep:02} 期 · {c['date']}</span><p>原题在正文各课末尾，原答案在后半部分，点击展开。</p><div class="actions"><button data-learn="{ep}">读完了，加入复习</button><a href="../originals/{ep:03}.md" download>下载原文</a><button id="toggle-answers">展开全部答案</button></div><p id="learn-status" role="status"></p></div><article class="prose">{article}</article></div></main>'''
        (out / 'courses' / f'{ep:03}.html').write_text(page(f'第{ep}期', content, '../', f'data-course="{ep}"'), encoding='utf-8')
        (out / 'originals' / f'{ep:03}.md').write_text(c['body'], encoding='utf-8')
    missing_label = '、'.join(map(str, report['missing_episodes']))
    banner = f'<div class="notice"><strong>当前原文覆盖 {report["complete_count"]}/{report["expected_count"]} 期</strong><span>缺失期号：{missing_label}；未用摘要或新写内容代替。<a href="./status.html">查看详情 ↗</a></span></div>' if report['missing_episodes'] else '<div class="notice">历史课程完整性检查已通过。</div>'
    main = f'''<main class="library"><section class="hero"><div><p class="eyebrow">THE DAILY ALGORITHM LIBRARY</p><h1>读懂算法，<br>也读懂它的边界。</h1><p class="hero-copy">从一个寓言开始，把机制、证据与思考留在一起。<br>每天一点，反复回忆，逐渐形成自己的知识体系。</p></div><div class="hero-note"><span>今日学习节奏</span><strong>读 · 想 · 验</strong><p>先读故事 → 独立答题<br>展开原答案 → 间隔复习</p><a href="./review.html">去复习 →</a></div></section>{banner}<section class="catalog"><div class="section-top"><div><p class="eyebrow">YOUR COLLECTION</p><h2>课程目录 <span>{len(courses)} 期原文</span></h2></div><label class="search-box"><span>全文检索</span><input id="search" type="search" placeholder="搜索概念、正文、原题或答案…" autocomplete="off"></label></div><p id="search-status" class="muted" role="status">按期数倒序 · 原文与原题均可搜索</p><div id="course-grid" class="course-grid">{''.join(cards)}</div><p id="empty" hidden>没有找到匹配课程，换个关键词试试。</p></section></main>'''
    (out / 'index.html').write_text(page('课程目录', main), encoding='utf-8')
    review = '<main class="library"><p class="eyebrow">ACTIVE RECALL</p><h1>让记忆，走得更远。</h1><p class="muted">读完课程后，按D+1、D+7、D+30安排复习。先回答，再展开原答案。进度保存在当前浏览器，可导出备份。</p><div class="actions"><button id="export-progress">导出进度</button><label class="button secondary">导入进度<input id="import-progress" type="file" accept="application/json" hidden></label></div><p id="progress-status" role="status"></p><div id="review-list"></div></main>'
    (out / 'review.html').write_text(page('间隔复习', review), encoding='utf-8')
    missing = '、'.join(map(str, report['missing_episodes'])) or '无'
    rows = ''.join(f'<tr><td>第{c["episode"]}期</td><td>{c["date"]}</td><td>9 / 9</td><td><a href="./originals/{c["episode"]:03}.md">原文</a></td><td><code>{c["body_sha256"][:16]}</code></td></tr>' for c in courses)
    status = f'''<main class="library"><p class="eyebrow">CONTENT & PROVENANCE</p><h1>内容与更新状态</h1><div class="notice"><strong>完整原文 {len(courses)} / {report['expected_count']} 期 · 原题{report['question_count']}道 / 原答案{report['answer_count']}份</strong><span>缺失期号：{missing}。原项目尚未恢复；此版本为可继续导入的恢复站点。</span></div><h2>自动更新边界</h2><p>ChatGPT每日10点任务的输出接入：<strong>尚未验证</strong>。网站构建成功与任务接入成功是两个独立状态。</p><p>GitHub Actions在北京时间10:15与10:45检查当天原文入站文件；本机跟进读取授权原聊天后提交。缺少当天原文、内容不完整或构建失败会停止发布并保留现有站点。</p><h2>最近一次自动入库</h2><p id="sync-status">正在读取入库证据…</p><p><a href="./sync.json">入库证据JSON</a> · <a href="https://github.com/tengtenglf/ai-algorithm-library/actions">GitHub Actions运行记录</a></p><h2>原始资料</h2><p>来源：原聊天 <a href="https://chatgpt.com/c/6ac9e367-6ea8-83ec-aeee-555083ffcfb7">每日 AI 算法寓言</a>。逐条保留可读消息正文，下载文件与校验哈希对应。未对课程中的研究事实作重新审校。</p><p>有 {report['unresolved_citations']} 个ChatGPT内部引用未解析，显示为“原聊天引用：未解析”，没有编造外部网址。课程中的外部网址只检查格式，网络可达性结果见交付报告。</p><div class="table-wrap"><table><thead><tr><th>课程</th><th>日期</th><th>原题 / 原答案</th><th>下载</th><th>SHA256前16位</th></tr></thead><tbody>{rows}</tbody></table></div><p><a href="./audit.json">下载内容审计JSON</a></p></main>'''
    (out / 'status.html').write_text(page('内容与更新状态', status), encoding='utf-8')
    (out / 'data.json').write_text(json.dumps(courses, ensure_ascii=False), encoding='utf-8')
    (out / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    ledger = root / 'content/sync/latest.json'
    if ledger.exists():
        shutil.copy2(ledger, out / 'sync.json')
    return report


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs: self.ids.add(attrs['id'])
        for key in ['href', 'src']:
            if key in attrs: self.links.append(attrs[key])


def check_links(root):
    out = root / 'dist'
    parsers = {}
    for path in out.rglob('*.html'):
        parser = Links(); parser.feed(path.read_text(encoding='utf-8')); parsers[path.resolve()] = parser
    checked, external, errors = 0, set(), []
    for path, parser in parsers.items():
        for link in parser.links:
            url = urllib.parse.urlsplit(link)
            if url.scheme:
                if url.scheme not in ['https', 'http', 'mailto']:
                    errors.append(f'不支持的链接协议：{link}')
                elif url.scheme in ['https', 'http']:
                    if not url.hostname: errors.append(f'无主机名：{link}')
                    external.add(link)
                continue
            target = (path.parent / urllib.parse.unquote(url.path)).resolve() if url.path else path
            checked += 1
            if not target.is_relative_to(out.resolve()) or not target.is_file():
                errors.append(f'{path.name} → {link}')
            elif url.fragment and target in parsers and urllib.parse.unquote(url.fragment) not in parsers[target].ids:
                errors.append(f'锚点不存在：{path.name} → {link}')
    if errors: raise ValueError('\n'.join(errors))
    return {'internal_links_checked': checked, 'external_unique_urls': len(external), 'external_urls': sorted(external)}


def fetch_feed(url):
    def check(value):
        p = urllib.parse.urlsplit(value)
        if p.scheme != 'https' or not p.hostname or p.username or p.password:
            raise ValueError('需配置不含凭据的HTTPS Feed URL；不能从ChatGPT页面URL直接获取课程')
        addresses = socket.getaddrinfo(p.hostname, 443)
        if any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('Feed不能指向本机或内网地址')
    check(url)
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            check(newurl)
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent':'AI-Algorithm-Library/1.0'})
    with urllib.request.build_opener(Redirect()).open(request, timeout=40) as response:
        data = response.read(10_000_001)
    if len(data) > 10_000_000: raise ValueError('Feed超过10MB，拒绝导入')
    payload = json.loads(data)
    messages, conversation = messages_from_payload(payload)
    if not messages: raise ValueError('Feed没有课程消息，不能视作成功同步')
    return messages, conversation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['import', 'fetch', 'audit', 'build', 'links'])
    parser.add_argument('file', nargs='?')
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--require-today', action='store_true')
    args = parser.parse_args()
    if args.command == 'import':
        payload = json.loads(Path(args.file).read_text(encoding='utf-8')) if args.file else json.load(sys.stdin)
        messages, conv = messages_from_payload(payload)
        print(json.dumps({'imported': import_messages(ROOT, messages, conv)}, ensure_ascii=False))
    elif args.command == 'fetch':
        messages, conv = fetch_feed(os.environ.get('COURSE_FEED_URL', ''))
        if args.require_today:
            today = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
            parsed = [parse_course(m['text'], m['id'], conv) for m in messages if re.search(r'第\s*\d+\s*期[｜|]', m.get('text',''))]
            if not any(c['date'] == today for c in parsed):
                raise ValueError(f'Feed尚无北京时间{today}课程；保留现有站点并报告本次更新失败')
        print(json.dumps({'imported': import_messages(ROOT, messages, conv)}, ensure_ascii=False))
    elif args.command == 'audit': print(json.dumps(audit(ROOT, args.require_complete), ensure_ascii=False, indent=2))
    elif args.command == 'build': print(json.dumps(build(ROOT), ensure_ascii=False, indent=2))
    else: print(json.dumps(check_links(ROOT), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'ERROR: {error}', file=sys.stderr); sys.exit(1)
