"""Sync a minimized SQLite snapshot to the owner-private GWC dashboard."""
import argparse
import getpass
import json
import os
import sys
import time
import urllib.request
from urllib.parse import urlparse
from export_analytics import snapshot


def push(database,url,token):
    if urlparse(url).scheme!='https': raise ValueError('Sync requires an HTTPS Site URL.')
    payload=json.dumps(snapshot(database)).encode()
    request=urllib.request.Request(url.rstrip('/')+'/api/snapshot',data=payload,
        headers={'Content-Type':'application/json','OAI-Sites-Authorization':'Bearer '+token},method='POST')
    with urllib.request.urlopen(request,timeout=30) as response:
        result=json.load(response)
        if not result.get('ok'):raise RuntimeError('Snapshot was not accepted')
    print('Analytics synced successfully.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('database');p.add_argument('--url',required=True);p.add_argument('--watch',action='store_true');p.add_argument('--token-stdin',action='store_true')
    a=p.parse_args()
    token=sys.stdin.readline().strip() if a.token_stdin else os.environ.get('GWC_ANALYTICS_TOKEN') or getpass.getpass('Dashboard service token (hidden): ')
    if not token:raise SystemExit('A dashboard service token is required.')
    while True:
        try:push(a.database,a.url,token)
        except Exception as error:
            print('Sync failed ('+type(error).__name__+'). The online dashboard keeps its previous snapshot.',flush=True)
            if not a.watch:raise SystemExit(1)
        if not a.watch:break
        time.sleep(60)
