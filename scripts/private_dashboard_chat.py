#!/usr/bin/env python3
"""Send authorized Chat attachments to the SAME private API used by the UI.

Run only in a trusted runtime with the owner's endpoint/token configured in the
environment. This is not a ChatGPT background listener or Library connector.
"""
from __future__ import annotations
import argparse
import base64
from datetime import date
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.private_dashboard_inputs import MAX_FILE, MAX_REQUEST
from scripts.private_dashboard_store import checked_path

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise HTTPError(request.full_url,code,'Private upload redirect refused',headers,fp)

class Client:
    def __init__(self,origin,token,*,allow_http_loopback=False):
        parsed=urlsplit(origin)
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or not parsed.hostname:
            raise ValueError('INVALID_PRIVATE_ORIGIN')
        if parsed.scheme!='https' and not (allow_http_loopback and parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','::1','localhost')):
            raise ValueError('HTTPS_REQUIRED')
        if not isinstance(token,str) or len(token)<32 or any(ord(c)<33 or ord(c)>126 for c in token):
            raise ValueError('PRIVATE_TOKEN_REQUIRED')
        self.origin=origin;self.token=token;self.opener=build_opener(NoRedirect())
    def call(self,path,body=None):
        if path not in ('prepare','apply','status'):raise ValueError('INVALID_API_ROUTE')
        raw=json.dumps(body,ensure_ascii=False,allow_nan=False).encode() if body is not None else None
        if raw and len(raw)>MAX_REQUEST:raise ValueError('UPLOAD_TOO_LARGE')
        request=Request(self.origin+'/api/private-intake/'+path,data=raw,
                        headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json','Accept':'application/json'},
                        method='POST' if body is not None else 'GET')
        try:
            with self.opener.open(request,timeout=60) as response:
                if response.geturl()!=request.full_url:raise ValueError('REDIRECT_REJECTED')
                if 'application/json' not in response.headers.get('Content-Type',''):raise ValueError('INVALID_API_RESPONSE')
                data=response.read(256*1024+1)
                if len(data)>256*1024:raise ValueError('API_RESPONSE_TOO_LARGE')
                return json.loads(data)
        except HTTPError as exc:
            try:
                value=json.loads(exc.read(4096));code=value.get('reason','HTTP_REQUEST_FAILED')
                if not isinstance(code,str) or not re.fullmatch('[A-Z_]{1,80}',code):code='HTTP_REQUEST_FAILED'
            except (ValueError,AttributeError):code='HTTP_REQUEST_FAILED'
            finally:exc.close()
            raise ValueError(code) from None
        except (URLError,TimeoutError,OSError):raise ValueError('PRIVATE_API_UNREACHABLE') from None

def source(kind,path):
    path=checked_path(path)
    if not path.is_file() or not 0<path.stat().st_size<=MAX_FILE:raise ValueError('INVALID_SOURCE_SIZE')
    raw=path.read_bytes()
    if len(raw)>MAX_FILE:raise ValueError('SOURCE_GREW')
    return {'kind':kind,'content_b64':base64.b64encode(raw).decode('ascii')}

def confirmations(values):
    result={}
    for value in values:
        match=re.fullmatch(r'(\d{4}-\d{2}-\d{2})=(\d{1,3})',value)
        if not match:raise ValueError('INVALID_OWNER_CONFIRMATION')
        night,number=match.group(1),int(match.group(2));date.fromisoformat(night)
        if number>100 or night in result:raise ValueError('INVALID_OWNER_CONFIRMATION')
        result[night]=number
    return result

def repeat_result(prepared,confirmed):
    if confirmed and confirmed!=prepared['applied_confirmations']:
        raise ValueError('ALREADY_APPLIED_DIFFERENT_CONFIRMATIONS')
    return {'state':'APPLIED','receipt_id':prepared['receipt_id'],'revision':prepared['applied_revision'],'duplicate':True}

def make_batch(prepared,confirmed):
    return {'schema_version':'habu-local-intake-review-batch-v1','baseline_asof':prepared['asof'],
            'source_sha256':prepared['source_sha256'],'requires_server_reconciliation':True,
            'counts_are_owner_confirmed_not_scientific_labels':True,
            'files':[{'path':f'data/raw/habu_owner_nights/{night[:4]}/{night}.json',
                      'content':{'schema_version':'habu-owner-night-v1','source':'user Habu log',
                                 'operational_date':night,'owner_confirmed':True,'search_performed':True,
                                 'capture_count':count,'revision':1}} for night,count in sorted(confirmed.items())]}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log',type=Path,action='append',default=[])
    parser.add_argument('--gpx',type=Path,action='append',default=[])
    parser.add_argument('--confirm',action='append',default=[],metavar='YYYY-MM-DD=COUNT',
                        help='Only explicit owner-confirmed personal captures; never infer zero from GPX')
    args=parser.parse_args()
    try:
        client=Client(os.environ.get('HABU_DASHBOARD_ORIGIN',''),os.environ.get('HABU_DASHBOARD_TOKEN',''))
        confirmed=confirmations(args.confirm)
        files=[source(kind,path) for kind,paths in [('log',args.log),('gpx',args.gpx)] for path in paths]
        if not files:raise ValueError('SOURCE_REQUIRED')
        prepared=client.call('prepare',{'files':files,'channel':'chat'})
        if prepared['state']=='APPLIED':result=repeat_result(prepared,confirmed)
        elif prepared['state']=='HELD' or not confirmed:
            result={key:prepared[key] for key in ('state','receipt_id','revision','archived_sources','reasons')}
        else:
            result=client.call('apply',{'receipt_id':prepared['receipt_id'],'batch':make_batch(prepared,confirmed),
                                       'expected_revision':prepared['revision']})
        if result['state']=='APPLIED':
            state=client.call('status')
            if state['revision']<result['revision']:raise ValueError('READBACK_FAILED')
            result['readback_verified']=True
        print(json.dumps(result,ensure_ascii=False))
        return 2 if result['state']=='HELD' else 0
    except (ValueError,KeyError,OSError) as exc:
        code=str(exc)
        if not re.fullmatch('[A-Z_]{1,80}',code):code='PRIVATE_UPLOAD_FAILED'
        print(json.dumps({'state':'ERROR','reason':code}),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
