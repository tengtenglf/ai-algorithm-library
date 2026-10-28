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
    if source_path.name != f'{target_date}.json':
        raise ValueError('入站文件名必须与目标日期一致')
    payload=json.loads(source_path.read_text(encoding='utf-8'))
    messages,conversation=library.messages_from_payload(payload)
    if conversation=='unknown':raise ValueError('原聊天ID缺失')
    parsed=[library.parse_course(m['text'],m['id'],conversation,m.get('delivery')) for m in messages]
    if not parsed or any(c['date']!=target_date for c in parsed):
        raise ValueError(f'未取得北京时间{target_date}的完整课程；保留现有站点')
    added=library.import_messages(root,messages,conversation)
    report=library.audit(root)
    return {'schema_version':1,'checked_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
            'target_date':target_date,'source_conversation_id':conversation,
            'source_message_ids':[c['source']['message_id'] for c in parsed],
            'source_delivery_ids':[c['source'].get('delivery',{}).get('id') for c in parsed],
            'source_episodes':[c['episode'] for c in parsed],
            'source_sha256':[c['body_sha256'] for c in parsed],
            'processed':len(parsed),'imported':added,
            'complete_count':report['complete_count'],'expected_count':report['expected_count'],
            'missing_episodes':report['missing_episodes'],
            'chatgpt_task_direct_output':report['chatgpt_task_output_bridge']}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='')
    p.add_argument('--date',default='',help='补投日期YYYY-MM-DD；留空检查北京时间今天')
    p.add_argument('--report',required=True)
    args=p.parse_args()
    today=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    target=args.date or today
    source=ROOT/args.source if args.source else ROOT/'content/inbox'/f'{target}.json'
    try:
        if date.fromisoformat(target).isoformat()!=target or target>today:
            raise ValueError('目标日期必须为YYYY-MM-DD，且不能晚于北京时间今天')
        report=sync(ROOT,target,source)
        report['status']='success'
    except (ValueError,OSError,KeyError,TypeError) as error:
        report={'schema_version':1,'checked_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                'target_date':target,'status':'failed',
                'error_code':'missing_inbox' if isinstance(error,FileNotFoundError) and error.filename==str(source.resolve()) else 'invalid_source_or_sync',
                'error':str(error)}
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'ERROR: {error}',file=sys.stderr)
        return 1
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    ledger=ROOT/'content/sync/latest.json'
    old=json.loads(ledger.read_text()) if ledger.exists() else {}
    if (report['imported'] or old.get('complete_count')!=report['complete_count']
            or old.get('chatgpt_task_direct_output')!=report['chatgpt_task_direct_output']):
        ledger.parent.mkdir(parents=True,exist_ok=True)
        ledger.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
