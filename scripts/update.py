#!/usr/bin/env python3
"""Consume original daily messages from the authorized inbox; no generation."""
import argparse,json,sys
from datetime import date,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import library

ROOT=Path(__file__).resolve().parents[1]

def sync(root,target_date,source_path):
    date.fromisoformat(target_date)
    source_path=source_path.resolve()
    inbox=(root/'content/inbox').resolve()
    if not source_path.is_relative_to(inbox):
        raise ValueError('来源必须位于content/inbox，不能读取任意仓库文件')
    payload=json.loads(source_path.read_text(encoding='utf-8'))
    messages,conversation=library.messages_from_payload(payload)
    if conversation=='unknown':raise ValueError('原聊天ID缺失')
    parsed=[library.parse_course(m['text'],m['id'],conversation) for m in messages]
    if not parsed or any(c['date']!=target_date for c in parsed):
        raise ValueError(f'未取得北京时间{target_date}的完整课程；保留现有站点')
    added=library.import_messages(root,messages,conversation)
    report=library.audit(root)
    return {'schema_version':1,'checked_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
            'target_date':target_date,'source_conversation_id':conversation,
            'source_message_ids':[c['source']['message_id'] for c in parsed],
            'source_episodes':[c['episode'] for c in parsed],
            'source_sha256':[c['body_sha256'] for c in parsed],
            'processed':len(parsed),'imported':added,
            'complete_count':report['complete_count'],'expected_count':report['expected_count'],
            'missing_episodes':report['missing_episodes'],
            'chatgpt_task_direct_output':'not_verified'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='')
    p.add_argument('--report',required=True)
    args=p.parse_args()
    today=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    source=ROOT/args.source if args.source else ROOT/'content/inbox'/f'{today}.json'
    report=sync(ROOT,today,source)
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    ledger=ROOT/'content/sync/latest.json'
    if report['imported'] or not ledger.exists():
        ledger.parent.mkdir(parents=True,exist_ok=True)
        ledger.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
