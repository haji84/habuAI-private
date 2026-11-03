"""Offline boot regression for the mobile HABU field recorder.

Simulates cache installation under authenticated content, restarts with the
network unreachable, validates background-free GPS recording code paths, and
guards against relying on stale aggregate data for fresh owner certification.
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_capture_dashboard as builder

ROOT=Path(__file__).resolve().parents[1]
DASH=ROOT/"dashboard"

SW_SIM=r"""
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const script=fs.readFileSync('dashboard/sw.js','utf8');
const base='https://hub-natural-private.pages.dev/';
const registered={};
let offline=false;
class FakeRequest {
 constructor(url,opts){this.url=String(url);this.method='GET';this.opts=opts||{};}
}
class FakeResponse {
 constructor(body,{ok=true,redirected=false,type='basic',headers={}}={}){
  this.body=body;this.ok=ok;this.redirected=redirected;this.type=type;
  this.headers={get:(key)=>headers[key.toLowerCase()]||null};
 }
 clone(){return new FakeResponse(this.body,{ok:this.ok,redirected:this.redirected,type:this.type,
  headers:{'content-type':this.headers.get('content-type')}});}
 static error(){return new FakeResponse('OFFLINE_NETWORK_FAILED',{ok:false,type:'error'});}
}
const buckets=new Map();
const cacheFor=(name)=>{
 if(!buckets.has(name))buckets.set(name,new Map());
 const bucket=buckets.get(name);
 return {
  put:async(req,res)=>bucket.set(typeof req==='string'?req:req.url,res.clone()),
  match:async req=>bucket.get(typeof req==='string'?req:req.url)
 };
};
const api={
 open:async name=>cacheFor(name),
 keys:async()=>[...buckets.keys()],
 delete:async name=>buckets.delete(name),
 match:async (req,opts)=>{
  const key=typeof req==='string'?req:req.url;
  if(opts&&opts.cacheName)return buckets.get(opts.cacheName)?.get(key);
  for(const items of buckets.values()){if(items.has(key))return items.get(key);}
  return undefined;
 }
};
const respond=async (path,ev)=>{
 const listener=registered.fetch;
 let response;
 listener({request:new FakeRequest(base+path),respondWith(p){response=p;},waitUntil(p){Promise.resolve(p).catch(()=>{});}});
 if(!response)throw Error('Request not handled: '+path);
 return await response;
};
async function run(){
 const context={
  URL,Request:FakeRequest,Response:FakeResponse,Promise,Set,caches:api,
  self:{registration:{scope:base},clients:{claim:async()=>{}},skipWaiting:async()=>{},
    addEventListener:(name,cb)=>registered[name]=cb},
  fetch:async (req)=>{
   if(offline)throw Error('network offline');
   const path=new URL(req.url||req).pathname;
   let ct=path.endsWith('.js')?'application/javascript':
     path.endsWith('.html')||path==='/'?'text/html':
     path.endsWith('.json')?'application/json':
     path.endsWith('.webmanifest')?'application/manifest+json':'image/png';
   return new FakeResponse('ASSET '+path,{headers:{'content-type':ct}});
  }
 };
 vm.runInNewContext(script,context,{filename:'sw.js'});
 let installed;
 registered.install({waitUntil(p){installed=p}});
 await installed;
 let active;
 registered.activate({waitUntil(p){active=p}});
 await active;
 offline=true;
 assert((await respond('field.html')).body.includes('/field.html'));
 assert((await respond('field-core.js')).body.includes('/field-core.js'));
 assert((await respond('field-app.js')).body.includes('/field-app.js'));
 assert((await respond('intake.html')).body.includes('/intake.html'));
 assert((await respond('index.html')).body.includes('/index.html'));
 const message=await new Promise(resolve=>{
  let pending;
  registered.message({data:{type:'HABU_FIELD_OFFLINE_STATUS'},
    ports:[{postMessage:resolve}],waitUntil(p){pending=p;}});
 });
 assert.equal(message.ready,true);
 assert.equal(message.type,'HABU_FIELD_OFFLINE_STATUS');
 const stale=await respond('data/capture_summary.json?require_fresh=1');
 assert.equal(stale.ok,false);
 const cached=api.match(base+'field.html');
 assert((await cached).body.includes('/field.html'));
 // Access redirects during installation must never be cached as the field app.
 buckets.clear();offline=false;
 context.fetch=async(req)=>{
  const path=new URL(req.url||req).pathname;
  if(path.endsWith('field-app.js'))return new FakeResponse('LOGIN',{headers:{'content-type':'text/html'},redirected:true});
  return new FakeResponse('OK',{headers:{'content-type':path.endsWith('.js')?'application/javascript':path.endsWith('.html')||path==='/'?'text/html':'application/json'}});
 };
 let failed;
 registered.install({waitUntil(p){failed=p;}});
 await assert.rejects(failed,/Offline shell requires authenticated/);
 assert.equal((await api.keys()).length,0);
 console.log('OFFLINE_FIELD_SW_PASS');
}
run().catch(e=>{console.error(e);process.exit(1);});
"""


class OfflineFieldTests(unittest.TestCase):
    def emitted_fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        repo = Path(temp.name)
        dash = repo / 'dashboard'
        (dash / 'assets').mkdir(parents=True)
        for name in ('sw.js', 'manifest.webmanifest', '_headers', 'intake.html',
                     'intake-core.js', 'field.html', 'field-core.js', 'field-app.js',
                     'field.webmanifest', 'assets/logo.png'):
            (dash / name).write_bytes((DASH / name).read_bytes())
        (dash / 'index.html').write_bytes(b'<script id="snapshot" type="application/json">{}</script>')
        return repo

    def emit_worker(self, repo, stamp='2026-11-04T00:00:00Z'):
        with patch.object(builder, 'build', return_value={'generated_at_utc': stamp}):
            builder.emit(repo)
        text = (repo / 'dashboard/dist/sw.js').read_text(encoding='utf-8')
        token = re.search(r"^const CACHE = '([^']+)';$", text, re.M).group(1)
        return text, token

    def test_emitted_worker_revision_changes_with_shell_bytes_but_not_build_clock(self):
        repo = self.emitted_fixture()
        first, token = self.emit_worker(repo)
        self.assertEqual(self.emit_worker(repo), (first, token))
        self.assertEqual(self.emit_worker(repo, '2026-11-05T00:00:00Z'), (first, token))
        for name in ('field-core.js', 'field-app.js', 'intake-core.js', 'field.html',
                     'intake.html', 'index.html', 'field.webmanifest', 'sw.js'):
            with self.subTest(asset=name):
                path = repo / 'dashboard' / name
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b'\n/* synthetic shell revision */\n')
                    changed, changed_token = self.emit_worker(repo)
                    self.assertNotEqual(changed_token, token)
                    self.assertNotEqual(changed, first)
                    self.assertEqual(path.read_bytes(), original + b'\n/* synthetic shell revision */\n')
                finally:
                    path.write_bytes(original)

    @unittest.skipUnless(shutil.which('node'), 'Node.js required')
    def test_failed_built_asset_upgrade_preserves_active_offline_shell(self):
        repo = self.emitted_fixture()
        first, _ = self.emit_worker(repo)
        path = repo / 'dashboard/field-app.js'
        path.write_bytes(path.read_bytes() + b'\n/* synthetic asset-only update */\n')
        second, _ = self.emit_worker(repo)
        harness = SW_SIM.replace(
            "const script=fs.readFileSync('dashboard/sw.js','utf8');",
            'const script=' + json.dumps(first) + ';\nconst nextScript=' + json.dumps(second) + ';')
        controls = r'''
 const oldListeners={...registered};
 const oldBuckets=await api.keys();
 const nextContext={...context,self:{...context.self},fetch:async req=>{
  const path=new URL(req.url||req).pathname;
  if(path.endsWith('field-app.js'))throw Error('synthetic upgrade failure');
  return new FakeResponse('NEW '+path,{headers:{'content-type':path.endsWith('.js')?'application/javascript':path.endsWith('.html')||path==='/'?'text/html':'image/png'}});
 }};
 vm.runInNewContext(nextScript,nextContext,{filename:'next-built-sw.js'});
 let failedUpgrade;registered.install({waitUntil(p){failedUpgrade=p;}});
 await assert.rejects(failedUpgrade,/synthetic upgrade failure/);
 for(const name of oldBuckets)assert(buckets.has(name),'Active shell was deleted');
 Object.assign(registered,oldListeners);offline=true;
 assert.equal((await respond('field-core.js')).body,'ASSET /field-core.js');
 assert.equal((await respond('field-app.js')).body,'ASSET /field-app.js');
'''
        harness = harness.replace(' // Access redirects during installation', controls + '\n // Access redirects during installation')
        proc = subprocess.run(['node', '-e', harness], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_worker_generation_accepts_crlf_source_without_changing_it(self):
        repo = self.emitted_fixture()
        path = repo / 'dashboard/sw.js'
        original = path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        path.write_bytes(original)
        worker, token = self.emit_worker(repo)
        self.assertIn('hub-natural-static-', token)
        self.assertEqual(self.emit_worker(repo), (worker, token))
        self.assertEqual(path.read_bytes(), original)

    @unittest.skipUnless(shutil.which("node"),"Node.js required")
    def test_sw_caches_full_authenticated_shell_then_works_with_no_network(self):
        proc=subprocess.run(["node","-e",SW_SIM],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(proc.returncode,0,proc.stderr)

    def test_permissions_and_pwa_wiring(self):
        headers=(DASH/"_headers").read_text(encoding="utf-8")
        self.assertIn("Permissions-Policy: geolocation=(self)",headers)
        self.assertNotIn("geolocation=()",headers)
        html=(DASH/"field.html").read_text(encoding="utf-8")
        self.assertIn('href="./field.webmanifest"',html)
        self.assertIn('id="offlineState"',html)
        manifest=json.loads((DASH/"field.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["start_url"],"./field.html")
        app=(DASH/"field-app.js").read_text(encoding="utf-8")
        self.assertIn("navigator.serviceWorker.register('./sw.js'",app)
        self.assertIn("HABU_FIELD_OFFLINE_STATUS",app)
        self.assertIn("IndexedDB",app) if "IndexedDB" in app else self.assertIn("indexedDB",app)
        self.assertIn("require_fresh=1",app)
        self.assertIn("core.gpx(session)",app)
        self.assertIn("core.logfile(session)",app)
        self.assertIn("core.exportBackup(session)",app)

    def test_no_network_required_for_local_logs_and_gpx(self):
        js=r"""
const assert=require('node:assert/strict');
const c=require('./dashboard/field-core.js');
const s=c.createSession('night-session-abcdef987654321','2026-10-27T12:00:00Z');
c.recordPoint(s,{latitude:28.123,longitude:129.456,accuracy:8},'2026-10-27T12:00:10Z');
c.event(s,{id:'capture-event-0000000001',time:'2026-10-27T12:01:00Z',
 type:'capture',species:'ハブ',count:1,owner:'self'});
c.stop(s,'2026-10-27T12:15:00Z');
assert.match(c.gpx(s),/<trkpt/);
assert.match(c.logfile(s),/捕獲/);
assert.equal(c.summary(s)[0].ownerHabuCaptures,1);
const restored=JSON.parse(c.exportBackup(s));
assert.equal(restored.id,s.id);
console.log('OFFLINE_EXPORT_PASS');
"""
        if not shutil.which("node"):
            self.skipTest("Node.js required")
        proc=subprocess.run(["node","-e",js],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(proc.returncode,0,proc.stderr)

    def test_dashboard_build_bundles_offline_field_assets(self):
        builder=(ROOT/"scripts/build_capture_dashboard.py").read_text(encoding="utf-8")
        self.assertIn('"field.webmanifest"',builder)
        sw=(DASH/"sw.js").read_text(encoding="utf-8")
        for path in ["./field.webmanifest","./field-core.js","./field-app.js","./intake-core.js"]:
            self.assertIn(path,sw)
        self.assertNotIn("fetch('/api/",(DASH/"field-app.js").read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
