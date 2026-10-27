#!/usr/bin/env python3
"""Configure GitHub only after explicit account authentication; never force-push."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def run(*args, check=True):
    return subprocess.run(args, cwd=ROOT, check=check, text=True, capture_output=True)
def main():
    p=argparse.ArgumentParser(description='一键创建/连接GitHub仓库，设置Pages并触发首轮构建')
    p.add_argument('--repo',required=True,help='owner/ai-algorithm-library')
    p.add_argument('--visibility',choices=['public','private'],default='public')
    p.add_argument('--feed-url',default='')
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repo):
        raise ValueError('仓库名必须为owner/name')
    if a.feed_url and (not a.feed_url.startswith('https://') or '@' in a.feed_url):
        raise ValueError('Feed必须为无凭据的HTTPS URL')
    if run('gh','auth','status',check=False).returncode:
        print('尚未登录GitHub。请先执行 gh auth login，再重试本命令。',file=sys.stderr)
        return 2
    # A new empty repository is safe; do not merge or overwrite an existing project.
    existing=run('gh','repo','view',a.repo,'--json','nameWithOwner,defaultBranchRef',check=False)
    if not existing.returncode and json.loads(existing.stdout).get('defaultBranchRef'):
        raise ValueError('目标仓库已有历史，停止自动配置以保护现有项目；请在其checkout中人工合并本交付')
    if not (ROOT/'.git').exists():
        run('git','init','-b','main')
    run('git','add','--all')
    if run('git','diff','--cached','--quiet',check=False).returncode==1:
        run('git','-c','user.name=library-setup','-c','user.email=library-setup@users.noreply.github.com','commit','-m','Set up algorithm library')
    if existing.returncode:
        run('gh','repo','create',a.repo,'--'+a.visibility)
    remote='https://github.com/'+a.repo+'.git'
    old=run('git','remote','get-url','github',check=False)
    if old.returncode:
        run('git','remote','add','github',remote)
    elif old.stdout.strip()!=remote:
        raise ValueError('github remote已指向其他仓库，停止以保护现有配置')
    run('gh','auth','setup-git')
    # No force push. An existing history or race fails visibly.
    run('git','push','github','HEAD:main')
    run('gh','api','--method','PATCH',f'repos/{a.repo}','-f','default_branch=main')
    pages=run('gh','api',f'repos/{a.repo}/pages',check=False)
    method='PUT' if not pages.returncode else 'POST'
    run('gh','api','--method',method,f'repos/{a.repo}/pages','-f','build_type=workflow')
    if a.feed_url:
        run('gh','variable','set','COURSE_FEED_URL','--repo',a.repo,'--body',a.feed_url)
    run('gh','workflow','run','site.yml','--repo',a.repo,'--ref','main')
    result=run('gh','api',f'repos/{a.repo}/pages')
    print('配置完成。Pages返回地址（尚需检查部署结果）：'+json.loads(result.stdout)['html_url'])
    print(f'检查构建：gh run list --repo {a.repo} --workflow site.yml')
    if not a.feed_url: print('未配置COURSE_FEED_URL：每日导入会明确失败，ChatGPT任务输出接入仍未完成。')
    return 0
if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,subprocess.CalledProcessError) as e:
        print('配置未完成：'+(e.stderr if isinstance(e,subprocess.CalledProcessError) else str(e)),file=sys.stderr)
        sys.exit(1)
