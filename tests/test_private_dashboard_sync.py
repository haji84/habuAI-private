"""Synthetic integration tests. No actual owner log, location or GPX is used."""
import base64
from contextlib import closing
import hashlib
import importlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
LOG = 'ハブログ\r\n2026/11/01 18:00\r\nエリア探索開始\r\n2026/11/01 19:00\r\n捕獲\r\nハブ捕獲\r\n2026/11/01 20:00\r\nエリア探索終了\r\n'
GPX = b'<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1"><trk><trkseg><trkpt lat="0" lon="0"><time>2026-11-01T09:00:00Z</time></trkpt><trkpt lat="0" lon="0"><time>2026-11-01T11:00:00Z</time></trkpt></trkseg></trk></gpx>'

def upload(kind, raw):
    return {'kind': kind, 'content_b64': base64.b64encode(raw).decode('ascii')}

def batch(prepared, count=1, night='2026-11-01'):
    return {'schema_version':'habu-local-intake-review-batch-v1',
            'baseline_asof':prepared['asof'], 'source_sha256':prepared['source_sha256'],
            'requires_server_reconciliation':True,
            'counts_are_owner_confirmed_not_scientific_labels':True,
            'files':[{'path':f'data/raw/habu_owner_nights/{night[:4]}/{night}.json',
                      'content':{'schema_version':'habu-owner-night-v1', 'source':'user Habu log',
                                 'operational_date':night,'owner_confirmed':True,
                                 'search_performed':True,'capture_count':count,'revision':1}}]}

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'scripts/private_dashboard_store.py').is_file(),
                        'Shared Chat/dashboard private intake is not implemented')
        self.mod=importlib.import_module('scripts.private_dashboard_store')
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name); self.seed=self.base/'seed'; self.seed.mkdir()
        (self.seed/'dashboard').mkdir()
        baseline={'as_of_operational_night':'2026-10-30','months':[{'key':'2026-10','n':1}],
                  'nights':[{'night':'2026-10-30','month':'2026-10','count':1,'start':'不明','end':'不明','events':None}],
                  'notes':['SYNTHETIC TEST ONLY']}
        (self.seed/'dashboard/baseline_2026.json').write_text(json.dumps(baseline),encoding='utf-8')
        self.store=self.mod.Store(self.base/'private', self.seed, code_root=ROOT)
        self.files=[upload('log',LOG.encode()), upload('gpx',GPX)]
    def prepare(self):return self.store.prepare(self.files,channel='chat')
    def apply(self,p,count=1):return self.store.apply(p['receipt_id'],batch(p,count),p['revision'])
    def test_prepare_archives_exact_bytes_without_counting(self):
        p=self.prepare(); self.assertEqual(p['state'],'READY_FOR_CONFIRMATION')
        self.assertEqual(self.store.snapshot()['summary']['total'],1)
        with closing(sqlite3.connect(self.store.db_path)) as db:
            original=db.execute('SELECT body FROM blobs WHERE sha=?',(hashlib.sha256(LOG.encode()).hexdigest(),)).fetchone()[0]
        self.assertEqual(original,LOG.encode())
    def test_commit_rebuilds_actual_existing_builder_and_survives_reopen(self):
        p=self.prepare(); r=self.apply(p)
        self.assertEqual(r['state'],'APPLIED'); self.assertEqual(r['revision'],1)
        fresh=self.mod.Store(self.base/'private',self.seed,code_root=ROOT).snapshot()
        self.assertEqual(fresh['summary']['total'],2)
        self.assertEqual(fresh['summary']['effort']['total_nights'],2)
        self.assertTrue(fresh['summary']['effort']['not_negative_training_labels'])
    def test_cross_channel_repeat_and_lost_response_are_idempotent(self):
        p=self.prepare(); a=self.apply(p)
        q=self.store.prepare(list(reversed(self.files)),channel='dashboard')
        self.assertEqual(p['receipt_id'],q['receipt_id'])
        b=self.apply(p); self.assertEqual(a['revision'],b['revision'])
        self.assertEqual(self.store.snapshot()['summary']['total'],2)
    def test_zero_is_confirmed_not_inferred_from_gpx(self):
        p=self.prepare(); self.apply(p,0)
        s=self.store.snapshot()['summary']; self.assertEqual(s['total'],1)
        self.assertEqual(s['effort']['zero_nights'],1)
        only=self.store.prepare([upload('gpx',GPX)],channel='dashboard')
        self.assertEqual(only['state'],'HELD'); self.assertIn('LOG_REQUIRED_FOR_TALLY',only['reasons'])
    def test_stale_tab_rejected_without_partial_update(self):
        p=self.prepare(); self.apply(p)
        other=[upload('log',LOG.replace('11/01','11/02').encode())]
        q=self.store.prepare(other,channel='chat')
        with self.assertRaisesRegex(self.mod.SyncError,'REVISION_CONFLICT'):
            self.store.apply(q['receipt_id'],batch(q,night='2026-11-02'),0)
        self.assertEqual(self.store.snapshot()['summary']['total'],2)
    def test_same_night_different_source_never_double_adds(self):
        p=self.prepare(); self.apply(p)
        q=self.store.prepare([upload('log',(LOG+'\n').encode())],channel='chat')
        with self.assertRaises(self.mod.SyncError): self.apply(q)
        self.assertEqual(self.store.snapshot()['summary']['total'],2)
    def test_wrong_count_type_and_fake_hash_rejected(self):
        p=self.prepare(); b=batch(p);b['files'][0]['content']['capture_count']=True
        with self.assertRaises(self.mod.SyncError):self.store.apply(p['receipt_id'],b,0)
        b=batch(p);b['source_sha256']=['0'*64]
        with self.assertRaisesRegex(self.mod.SyncError,'SOURCE_HASH_MISMATCH'):self.store.apply(p['receipt_id'],b,0)
    def test_unobserved_night_not_accepted(self):
        p=self.prepare()
        with self.assertRaisesRegex(self.mod.SyncError,'LOG_NIGHT_MISMATCH'):
            self.store.apply(p['receipt_id'],batch(p,night='2026-11-02'),0)
    def test_gpx_date_mismatch_archived_but_held(self):
        p=self.store.prepare([upload('log',LOG.encode()),upload('gpx',GPX.replace(b'11-01',b'11-02'))],channel='chat')
        self.assertEqual(p['state'],'HELD');self.assertIn('GPX_LOG_NIGHT_CONFLICT',p['reasons'])
        with self.assertRaisesRegex(self.mod.SyncError,'RECEIPT_HELD'):self.apply(p)
    def test_gpx_dtd_nan_and_missing_time_are_held(self):
        bad=[b'<!DOCTYPE gpx [<!ENTITY x "x">]><gpx>&x;</gpx>',GPX.replace(b'lat="0"',b'lat="NaN"'),GPX.replace(b'<time>',b'<not-time>').replace(b'</time>',b'</not-time>')]
        for raw in bad:
            with self.subTest(raw=raw[:20]):
                p=self.store.prepare([upload('log',LOG.encode()),upload('gpx',raw)],channel='chat')
                self.assertEqual(p['state'],'HELD')
    def test_seven_am_boundary(self):
        text='ハブログ\n2026/11/02 06:59\n捕獲\nハブ捕獲\n2026/11/02 07:00\nエリア探索開始\n'
        p=self.store.prepare([upload('log',text.encode())],channel='chat')
        self.assertEqual([x['night'] for x in p['nights']],['2026-11-01','2026-11-02'])
    def test_raw_write_once_and_private_path_guard(self):
        self.prepare()
        with closing(sqlite3.connect(self.store.db_path)) as db:
            with self.assertRaises(sqlite3.DatabaseError):db.execute('UPDATE blobs SET body=?',(b'changed',))
        with self.assertRaises(self.mod.SyncError):self.mod.Store(self.seed/'private',self.seed,code_root=ROOT)
    def test_symlink_store_rejected(self):
        link=self.base/'link'
        try:link.symlink_to(self.base/'private',target_is_directory=True)
        except OSError:self.skipTest('platform cannot create symlink')
        with self.assertRaises(self.mod.SyncError):self.mod.Store(link,self.seed,code_root=ROOT)
    def test_transaction_rollback_when_build_fails(self):
        from unittest.mock import patch
        p=self.prepare()
        with patch('scripts.private_dashboard_store.build',side_effect=ValueError('synthetic disk/build failure')):
            with self.assertRaises(self.mod.SyncError):self.apply(p)
        self.assertEqual(self.store.snapshot()['revision'],0)
        self.assertEqual(self.store.snapshot()['summary']['total'],1)
        self.assertEqual(self.apply(p)['state'],'APPLIED')
    def test_simultaneous_duplicate_apply_commits_once(self):
        p=self.prepare()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.apply(p),range(2)))
        self.assertEqual([r['revision'] for r in results],[1,1])
    def test_cross_channel_provenance_and_retry_confirmations(self):
        p=self.prepare();self.apply(p)
        q=self.store.prepare(self.files,channel='dashboard')
        self.assertEqual(q['applied_confirmations'],{'2026-11-01':1})
        with closing(sqlite3.connect(self.store.db_path)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM channels').fetchone()[0],2)
    def test_dotdot_private_root_cannot_escape_into_checkout(self):
        escape=self.base/'unused'/'..'/'seed'/'new-private'
        with self.assertRaises(self.mod.SyncError):
            self.mod.Store(escape,self.seed,code_root=ROOT)
    def test_transient_parser_failure_can_be_retried(self):
        from unittest.mock import patch
        with patch('scripts.private_dashboard_inputs.subprocess.run',side_effect=OSError('synthetic missing Node')):
            with self.assertRaisesRegex(self.mod.SyncError,'LOG_PARSER_UNAVAILABLE'):self.prepare()
        self.assertEqual(self.prepare()['state'],'READY_FOR_CONFIRMATION')
    def test_multiple_new_nights_cannot_be_silently_partially_applied(self):
        text=LOG+LOG.replace('11/01','11/02')
        p=self.store.prepare([upload('log',text.encode())],channel='chat')
        with self.assertRaisesRegex(self.mod.SyncError,'ALL_NEW_NIGHTS_MUST_BE_CONFIRMED'):
            self.store.apply(p['receipt_id'],batch(p),p['revision'])
        self.assertEqual(self.store.snapshot()['revision'],0)
        b=batch(p);other=json.loads(json.dumps(b['files'][0]))
        other['path']=other['path'].replace('11-01','11-02')
        other['content']['operational_date']='2026-11-02';other['content']['capture_count']=0
        b['files'].append(other)
        self.store.apply(p['receipt_id'],b,p['revision'])
        self.assertEqual(self.store.snapshot()['summary']['total'],2)
    def test_raw_content_and_path_never_in_summary(self):
        p=self.prepare();self.apply(p)
        s=json.dumps(self.store.snapshot(),ensure_ascii=False)
        for forbidden in ['エリア探索開始','trkpt','content_b64',str(self.base)]:self.assertNotIn(forbidden,s)

class ApiTests(unittest.TestCase):
    def setUp(self):
        StoreTests.setUp(self)
        self.assertTrue((ROOT/'scripts/private_dashboard_api.py').is_file(),'Authenticated API is missing')
        from scripts.private_dashboard_api import Application
        self.token='synthetic-test-token-not-a-secret-'+'x'*40
        self.app=Application(self.store,ROOT/'dashboard',self.token,'https://owner.test')
    def request(self,path,method='GET',obj=None,auth=True,origin='https://owner.test',basic=False):
        body=json.dumps(obj).encode() if obj is not None else b''
        env={'REQUEST_METHOD':method,'PATH_INFO':path,'QUERY_STRING':'','CONTENT_LENGTH':str(len(body)),
             'CONTENT_TYPE':'application/json','wsgi.input':io.BytesIO(body),'wsgi.url_scheme':'https',
             'HTTP_HOST':'owner.test'}
        if origin:env['HTTP_ORIGIN']=origin
        if auth:env['HTTP_AUTHORIZATION']=('Basic '+base64.b64encode(('owner:'+self.token).encode()).decode()) if basic else 'Bearer '+self.token
        result={}
        def start(status,headers):result.update(status=int(status.split()[0]),headers=dict(headers))
        result['body']=b''.join(self.app(env,start));return result
    def test_no_unauthenticated_or_cross_origin_access(self):
        self.assertEqual(self.request('/api/private-intake/status',auth=False)['status'],401)
        self.assertEqual(self.request('/api/private-intake/prepare','POST',{'files':self.files},origin='https://other.test')['status'],403)
        self.assertEqual(self.request('/api/private-intake/prepare','POST',{'files':self.files},origin=None,basic=True)['status'],403)
    def test_actual_wsgi_prepare_apply_readback(self):
        r=self.request('/api/private-intake/prepare','POST',{'files':self.files,'channel':'chat'})
        self.assertEqual(r['status'],200);p=json.loads(r['body'])
        r=self.request('/api/private-intake/apply','POST',{'receipt_id':p['receipt_id'],'batch':batch(p),'expected_revision':0})
        self.assertEqual(r['status'],200)
        s=self.request('/data/capture_summary.json');self.assertEqual(json.loads(s['body'])['total'],2)
        self.assertIn('no-store',s['headers']['Cache-Control'])
    def test_existing_intake_ui_gets_upload_controller(self):
        r=self.request('/intake.html');self.assertEqual(r['status'],200)
        self.assertIn(b'private-intake.js',r['body']);self.assertIn(b'.gpx',r['body'])
        self.assertNotIn(b'async function loadSummary()',r['body'])
    def test_traversal_raw_and_unknown_route_not_served(self):
        for path in ['/../scripts/private_pdca_intake.py','/raw/x.gpx','/data/raw/habu_logs/file.txt']:
            self.assertEqual(self.request(path)['status'],404)
    def test_worker_private_routes_are_network_only(self):
        r=self.request('/sw.js');self.assertEqual(r['status'],200)
        text=r['body'].decode();self.assertIn('-private-sync-v1',text)
        self.assertNotIn("'./','./index.html',",text)
        self.assertIn("path.startsWith(new URL('./api/',BASE).pathname)",text)
        self.assertLess(text.index('event.respondWith(fetch(event.request));return;'),text.index('if(FIELD_SHELL.has(path))'))
    def test_index_is_rendered_from_committed_snapshot(self):
        template=self.base/'served';template.mkdir()
        (template/'index.html').write_text('<body><script id="snapshot" type="application/json">{}</script></body>')
        self.app.dashboard=template
        r=self.request('/');self.assertEqual(r['status'],200)
        self.assertIn(b'"total":1',r['body']);self.assertIn(b'private-intake.js',r['body'])
    def test_raw_sensitive_error_is_not_returned(self):
        r=self.request('/api/private-intake/apply','POST',{'bad':'PRIVATE_SENTINEL'})
        self.assertEqual(r['status'],400);self.assertNotIn(b'PRIVATE_SENTINEL',r['body'])

if __name__=='__main__':unittest.main()
