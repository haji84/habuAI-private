"""Authenticated same-origin WSGI adapter; no provider, billing or ACL mutation."""
from __future__ import annotations
import base64
import hmac
import json
import mimetypes
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from scripts.private_dashboard_store import Store, SyncError, canonical
from scripts.private_dashboard_inputs import MAX_REQUEST

ASSETS = {'index.html','intake.html','intake-core.js','private-intake.js','field.html','field-core.js',
          'field-app.js','field-quick.js','field-sync.js','field.webmanifest','manifest.webmanifest','sw.js',
          'assets/logo.png','assets/icon-192.png','assets/icon-512.png','assets/apple-touch-icon.png'}

class Application:
    def __init__(self, store, dashboard: Path, token: str, origin: str, *, allow_http_loopback=False):
        parsed=urlsplit(origin)
        if not isinstance(token,str) or len(token)<32 or any(ord(c)<33 or ord(c)>126 for c in token):
            raise ValueError('A private token of at least 32 printable ASCII characters is required')
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or not parsed.hostname:
            raise ValueError('Origin must contain only scheme and host')
        if parsed.scheme!='https' and not (allow_http_loopback and parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1')):
            raise ValueError('HTTPS required outside explicit loopback development')
        self.store=store;self.dashboard=Path(dashboard).resolve(strict=True)
        if store.root.is_relative_to(self.dashboard) or self.dashboard.is_relative_to(store.root):
            raise ValueError('Private storage must not overlap served files')
        self.token=token;self.origin=origin;self.host=parsed.netloc;self.scheme=parsed.scheme

    def auth(self, env):
        value=env.get('HTTP_AUTHORIZATION','')
        if value.startswith('Bearer '): candidate=value[7:];kind='bearer'
        elif value.startswith('Basic '):
            try:
                user,candidate=base64.b64decode(value[6:],validate=True).decode('ascii').split(':',1)
                if user!='owner':return None
            except (ValueError,UnicodeError):return None
            kind='basic'
        else:return None
        return kind if hmac.compare_digest(candidate.encode(),self.token.encode()) else None

    def __call__(self, env, start_response):
        status=200;kind='application/json; charset=utf-8';headers=[]
        try:
            if env.get('HTTP_HOST')!=self.host or env.get('wsgi.url_scheme')!=self.scheme:
                status=403;raise SyncError('ORIGIN_CONFIGURATION_MISMATCH')
            auth=self.auth(env)
            if auth is None:
                status=401;headers.append(('WWW-Authenticate','Basic realm="Habu private dashboard", charset="UTF-8"'))
                raise SyncError('AUTHENTICATION_REQUIRED')
            method,path=env.get('REQUEST_METHOD'),env.get('PATH_INFO','')
            if method not in ('GET','POST'):
                status=405;raise SyncError('METHOD_NOT_ALLOWED')
            if method=='POST':
                origin=env.get('HTTP_ORIGIN')
                if origin and origin!=self.origin or auth=='basic' and origin!=self.origin or env.get('HTTP_SEC_FETCH_SITE')=='cross-site':
                    status=403;raise SyncError('CROSS_ORIGIN_WRITE_REJECTED')
                if env.get('CONTENT_TYPE','').split(';')[0]!='application/json' or env.get('HTTP_CONTENT_ENCODING'):
                    status=415;raise SyncError('JSON_REQUIRED')
                try:length=int(env.get('CONTENT_LENGTH',''))
                except (ValueError,TypeError):
                    status=411;raise SyncError('CONTENT_LENGTH_REQUIRED') from None
                if not 0<length<=MAX_REQUEST:
                    status=413;raise SyncError('UPLOAD_TOO_LARGE')
                raw=env['wsgi.input'].read(length)
                if len(raw)!=length:raise SyncError('INCOMPLETE_REQUEST')
                try:obj=json.loads(raw)
                except (ValueError,UnicodeError):raise SyncError('INVALID_JSON') from None
                if not isinstance(obj,dict):raise SyncError('INVALID_REQUEST')
                if path=='/api/private-intake/prepare' and set(obj)=={'files','channel'}:
                    result=self.store.prepare(obj['files'],channel=obj['channel'])
                elif path=='/api/private-intake/apply' and set(obj)=={'receipt_id','batch','expected_revision'}:
                    result=self.store.apply(obj['receipt_id'],obj['batch'],obj['expected_revision'])
                else:raise SyncError('INVALID_REQUEST')
                body=canonical(result).encode()
            elif path=='/api/private-intake/status':
                snap=self.store.snapshot()
                body=canonical({'schema_version':'habu-private-dashboard-status-v1','revision':snap['revision'],
                                'asof':snap['summary']['asof'],'mode':'PRIVATE_DURABLE_STORE',
                                'scientific_training_eligible':False}).encode()
            elif path=='/data/capture_summary.json':body=canonical(self.store.snapshot()['summary']).encode()
            else:
                relative={'/':'index.html','/intake':'intake.html','/field':'field.html'}.get(path,path.lstrip('/'))
                if relative not in ASSETS:
                    status=404;raise SyncError('NOT_FOUND')
                asset=self.dashboard/relative
                if asset.is_symlink() or not asset.is_file() or not asset.resolve().is_relative_to(self.dashboard):
                    status=404;raise SyncError('NOT_FOUND')
                body=asset.read_bytes();kind=mimetypes.guess_type(relative)[0] or 'application/octet-stream'
                if relative in ('intake.html','index.html','sw.js'):
                    text=body.decode('utf-8')
                    if relative=='intake.html':
                        text,count=re.subn(r'<script>.*?</script>','<script src="./private-intake.js" defer></script>',text,flags=re.S)
                        if count!=1:raise SyncError('INTAKE_TEMPLATE_CHANGED')
                        text=text.replace('accept=".txt,.log,text/plain"','accept=".txt,.log,.gpx,text/plain,application/gpx+xml"')
                        text=text.replace('位置・座標はこの画面から外部送信しません。','原本はこの認証済みサイトの私有保存先へ送信します。公開GitHubには送りません。')
                        text=text.replace('ここではまず安全に確認用データを作る。','原本を私有保存した後、確認した捕獲数を画面へ反映します。')
                        text=text.replace('1. ログを選択する','1. ハブログ・GPXを選択する')
                        text=text.replace('日時付きのテキストログ（UTF-8）を複数選べます。','日時付きのハブログ（UTF-8）とGPXを複数選べます。')
                        text=re.sub(r'<section class="panel"><h2>3\. GitHubへ反映するには</h2>.*?</section>',
                          '<section class="panel"><h2>3. 確認して反映</h2><p>原本保存と集計反映は別です。探索夜ごとの本人捕獲数を確認し、「集計へ反映」を押してください。GPXだけで0匹や探索完了を決めつけません。学習・予想の更新は別工程です。</p></section>',text,flags=re.S)
                    elif relative=='index.html':
                        snapshot=canonical(self.store.snapshot()['summary']).replace('</','<\\/')
                        text,count=re.subn(r'(<script id="snapshot" type="application/json">).*?(</script>)',lambda m:m[1]+snapshot+m[2],text,count=1,flags=re.S)
                        if count!=1:raise SyncError('DASHBOARD_TEMPLATE_CHANGED')
                        text=text.replace('</body>','<script src="./private-intake.js" defer></script></body>')
                    else:
                        # Preserve offline field recorder assets and IndexedDB, but never
                        # cache private snapshots, intake API responses or owner tokens.
                        text=re.sub(r"(const CACHE = '[^']+)(';)",r"\1-private-sync-v1\2",text,count=1)
                        text=text.replace("'./','./index.html',", "'./private-intake.js',",1)
                        marker='  const path=url.pathname;'
                        if text.count(marker)!=1:raise SyncError('WORKER_TEMPLATE_CHANGED')
                        text=text.replace(marker,marker+"\n  if(path===SUMMARY_PATH || path===new URL('./',BASE).pathname || path===new URL('./index.html',BASE).pathname || path.startsWith(new URL('./api/',BASE).pathname)){event.respondWith(fetch(event.request));return;}")
                    body=text.encode('utf-8')
        except SyncError as exc:
            if str(exc)=='LOG_PARSER_UNAVAILABLE':status=503
            if status==200:status=409 if str(exc) in ('REVISION_CONFLICT','ALREADY_APPLIED_DIFFERENT_REQUEST','EXISTING_NIGHT_REVIEW_REQUIRED') else 400
            body=canonical({'state':'ERROR','reason':str(exc)}).encode();kind='application/json; charset=utf-8'
        except Exception:
            status=503;body=b'{"state":"ERROR","reason":"PRIVATE_SERVICE_UNAVAILABLE"}';kind='application/json; charset=utf-8'
        labels={200:'OK',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',405:'Method Not Allowed',409:'Conflict',411:'Length Required',413:'Content Too Large',415:'Unsupported Media Type',503:'Service Unavailable'}
        headers += [('Content-Type',kind),('Content-Length',str(len(body))),('Cache-Control','private, no-store'),
                    ('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Referrer-Policy','no-referrer'),
                    ('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")]
        if self.scheme=='https':headers.append(('Strict-Transport-Security','max-age=31536000'))
        start_response(f'{status} {labels[status]}',headers);return [body]

def create_app():
    repo=Path(__file__).resolve().parents[1]
    return Application(Store(Path(os.environ['HABU_PRIVATE_ROOT']),repo),repo/'dashboard',
                       os.environ['HABU_DASHBOARD_TOKEN'],os.environ['HABU_DASHBOARD_ORIGIN'])
