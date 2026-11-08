"""Field quick-entry and guarded automatic private sync (synthetic only).

No owner coordinates, network traffic, real-source writes or 30-minute device retest.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FieldQuickPrivateSyncTests(unittest.TestCase):
    def test_small_screen_quick_actions_and_detailed_form_remain_accessible(self):
        page = (ROOT / "dashboard/field.html").read_text(encoding="utf-8")
        for snippet in (
            'id="quickPanel"', 'id="quickStatus"',
            'data-quick-type="capture" data-quick-species="ハブ"',
            'data-quick-type="sighting" data-quick-species="ハブ"',
            'data-quick-type="roadkill" data-quick-species="ハブ"',
            'id="advancedRecord"', 'id="syncToggle"',
            'id="syncState"', 'id="syncConfirm"',
            'src="./field-quick.js"', 'src="./field-sync.js"',
        ):
            self.assertIn(snippet, page)
        self.assertNotIn('<details open', page)
        assert (ROOT / "dashboard/field-quick.js").is_file()
        assert (ROOT / "dashboard/field-sync.js").is_file()
        builder = (ROOT / "scripts/build_capture_dashboard.py").read_text(encoding="utf-8")
        worker = (ROOT / "dashboard/sw.js").read_text(encoding="utf-8")
        api = (ROOT / "scripts/private_dashboard_api.py").read_text(encoding="utf-8")
        for name in ('field-quick.js', 'field-sync.js'):
            self.assertIn(name, builder)
            self.assertIn(name, worker)
            self.assertIn(name, api)

    def test_sync_is_opt_in_and_never_uploads_before_private_service_attestation(self):
        js = (ROOT / "dashboard/field-sync.js").read_text(encoding="utf-8")
        self.assertIn("credentials:'omit'", js)
        self.assertIn("schema_version!=='habu-private-dashboard-status-v1'", js)
        self.assertIn("s.mode!=='PRIVATE_DURABLE_STORE'", js)
        self.assertLess(js.index('await status(); // No raw'),
                        js.index("const result=await request('./api/private-intake/prepare'"))
        self.assertIn("state:'HELD',reason:'LOCAL_SOURCE_REVIEW_REQUIRED'", js)
        self.assertIn("window.addEventListener('online'", js)
        self.assertIn("await put(syncDb,'meta',{id:'consent'", js)
        self.assertNotIn('localStorage', js.replace('never localStorage.', ''))
        self.assertNotIn('api.github.com', js)
        self.assertNotIn('cloudflare', js.lower())

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_actual_controller_quick_capture_and_non_capture_use_original_save_queue(self):
        from tests.test_field_writer_concurrency import HARNESS
        js = HARNESS + r"""
(async()=>{
const sourceQuick=fs.readFileSync('dashboard/field-quick.js','utf8');
const shared=database([fixture(false)]),tab=await controller(shared);
const get=tab.get;
get('add').click=()=>get('add').handlers.click();
get('species').options=[{value:'ハブ'},{value:'other'}];
const buttons=[
 {dataset:{quickType:'capture',quickSpecies:'ハブ',quickOwner:'self'},handlers:{},addEventListener(n,fn){this.handlers[n]=fn;}},
 {dataset:{quickType:'sighting',quickSpecies:'クロウサギ',quickOwner:'self'},handlers:{},addEventListener(n,fn){this.handlers[n]=fn;}}
];
tab.context.document.querySelectorAll=()=>buttons;
vm.runInNewContext(sourceQuick,tab.context,{filename:'field-quick.js'});
assert.equal(get('add').disabled,false);
buttons[0].handlers.click();await shared.idle();
let row=shared.rows.get('synthetic-session-0000001');
assert.equal(row.events.length,2);assert.equal(row.events[1].type,'capture');
assert.equal(row.events[1].species,'ハブ');assert.equal(row.events[1].owner,'self');
assert.equal(row.events[1].count,1);assert.equal(core.summary(row).reduce((t,n)=>t+n.ownerHabuCaptures,0),1);
buttons[1].handlers.click();await shared.idle();
row=shared.rows.get(row.id);
assert.equal(row.events.length,3);assert.equal(row.events[2].type,'sighting');
assert.equal(row.events[2].species,'クロウサギ');
assert.equal(core.summary(row).reduce((t,n)=>t+n.ownerHabuCaptures,0),1);
assert.equal(row.points.length,0,'quick tap must not fabricate a GPS fix');
assert.equal(get('species').value,'synthetic','old detailed form selection should remain');
assert.match(get('quickStatus').textContent,/端末に保存済み/);
const old=JSON.stringify(row);await tab.click('backup');
assert.equal(JSON.stringify(shared.rows.get(row.id)),old);
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-'],input=js,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_static_only_origin_causes_no_private_raw_posts(self):
        js=r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const calls=[],ui=new Map(),rows={meta:new Map(),receipts:new Map()};
function el(id){
 if(!ui.has(id))ui.set(id,{checked:false,disabled:true,dataset:{},textContent:'',handlers:{},
 addEventListener(n,cb){this.handlers[n]=cb;}});
 return ui.get(id);
}
function database(){
 const names=['meta','receipts'];
 const db={objectStoreNames:{contains:n=>names.includes(n)},createObjectStore:()=>{},
   close(){},transaction(name){
    const tx={oncomplete:null,onabort:null,onerror:null,objectStore(){
      return {
        get(key){const r={};setImmediate(()=>{r.result=rows[name].get(key);r.onsuccess?.()});return r;},
        getAll(){const r={};setImmediate(()=>{r.result=[...rows[name].values()];r.onsuccess?.()});return r;},
        put(value){setImmediate(()=>{rows[name].set(value.id,value);tx.oncomplete?.()});}
      };
    }};
    return tx;
   }};
 return db;
}
const db=database();
const idb={open(){const r={result:db};setImmediate(()=>{r.onupgradeneeded?.();r.onsuccess?.()});return r;}};
const context={console,Promise,Date,Number,TextEncoder,URL,location:{origin:'https://private.example'},
document:{baseURI:'https://private.example/field.html',visibilityState:'visible',getElementById:el,addEventListener(){}},
window:{indexedDB:idb,HabuFieldCore:{},addEventListener(){}},indexedDB:idb,navigator:{onLine:true},
fetch:async(url,opts)=>{calls.push({url,method:opts.method||'GET'});return {ok:false,status:404,redirected:false,headers:{get:()=>null}};}};
vm.runInNewContext(fs.readFileSync('dashboard/field-sync.js','utf8'),context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
for(let i=0;i<6;i++)await tick();
assert.match(el('syncState').textContent,/未設定/);
assert.equal(calls.length,0,'default OFF never probes or uploads');
el('syncToggle').checked=true;await el('syncToggle').handlers.change();
for(let i=0;i<8;i++)await tick();
assert(calls.length>=1,'server readiness must be checked');
assert(calls.every(c=>c.method==='GET'),'never send private input to static origin');
assert.match(el('syncState').textContent,/未接続/);
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-'],input=js,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)


    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_completed_session_uploads_once_then_explicit_owner_confirm_updates_snapshot(self):
        js=r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const core=require('./dashboard/field-core.js'),intake=require('./dashboard/intake-core.js');
const session=core.createSession('synthetic-sync-session-001','2026-11-02T10:00:00Z');
core.event(session,{id:'synthetic-capture-event-0001',type:'capture',species:'ハブ',
 count:1,owner:'self',time:'2026-11-02T10:01:00Z',note:'SYNTHETIC'});
core.stop(session,'2026-11-02T10:05:00Z');
const storage={'habu-field-local-v1':{sessions:new Map([[session.id,session]])},
 'habu-field-sync-v1':{meta:new Map(),receipts:new Map()}};
function database(name){
 const rows=storage[name];
 return {close(){},objectStoreNames:{contains:key=>!!rows[key]},
  createObjectStore(key){rows[key]=new Map();},
  transaction(key,mode){const tx={oncomplete:null,onabort:null,onerror:null,
    objectStore(){return{
      get(id){const req={};setImmediate(()=>{req.result=rows[key].get(id);req.onsuccess?.()});return req;},
      getAll(){const req={};setImmediate(()=>{req.result=[...rows[key].values()];req.onsuccess?.()});return req;},
      put(value){setImmediate(()=>{rows[key].set(value.id,value);tx.oncomplete?.()});}
    };}};return tx;}
 };
}
const idb={open(name){const req={result:database(name)};setImmediate(()=>{req.onupgradeneeded?.();req.onsuccess?.()});return req;}};
const ui=new Map(), calls=[];
function el(id){
 if(!ui.has(id))ui.set(id,{textContent:'',dataset:{},value:'',checked:false,disabled:true,
  handlers:{},addEventListener(n,fn){this.handlers[n]=fn;}});
 return ui.get(id);
}
let revision=0,asof='2026-10-30';
const response=(value)=>({ok:true,redirected:false,status:200,
 headers:{get:()=> 'application/json'},json:async()=>value});
async function fetchMock(url,opts){
 const path=new URL(url).pathname,method=opts.method||'GET',anon=opts.credentials==='omit';
 calls.push({path,method,anon});
 if(anon)return {ok:false,status:401,redirected:false,headers:{get:()=> 'application/json'}};
 if(path==='/api/private-intake/status')return response({
  schema_version:'habu-private-dashboard-status-v1',mode:'PRIVATE_DURABLE_STORE',
  revision,asof});
 if(path==='/api/private-intake/prepare'){
  assert.equal(method,'POST');
  const sent=JSON.parse(opts.body);
  assert.deepEqual(sent.files.map(x=>x.kind),['log']);
  assert.match(Buffer.from(sent.files[0].content_b64,'base64').toString('utf8'),/捕獲/);
  return response({state:'READY_FOR_CONFIRMATION',receipt_id:'a'.repeat(64),
    asof,revision,nights:[{night:'2026-11-02'}],source_sha256:['b'.repeat(64)]});
 }
 if(path==='/api/private-intake/apply'){
  assert.equal(method,'POST');
  const sent=JSON.parse(opts.body);
  assert.equal(sent.batch.files[0].content.capture_count,1);
  assert.equal(sent.expected_revision,0);
  revision=1;asof='2026-11-02';
  return response({state:'APPLIED',receipt_id:sent.receipt_id,revision:1});
 }
 if(path==='/data/capture_summary.json')return response({
  schema_version:'habu-capture-dashboard-v2',nights:[{night:'2026-11-02'}],
  privacy:'AGGREGATE_ONLY_NO_COORDINATES',asof,total:1});
 throw Error('Unexpected route '+path);
}
const context={console,Promise,Date,Number,URL,TextEncoder,btoa,Buffer,location:{origin:'https://private.example'},
 document:{baseURI:'https://private.example/field.html',visibilityState:'visible',getElementById:el,addEventListener(){}},
 window:{indexedDB:idb,HabuFieldCore:core,HabuLogIntake:intake,addEventListener(){}},
 indexedDB:idb,navigator:{onLine:true},fetch:fetchMock,
 prompt:()=>'1',confirm:()=>true};
vm.runInNewContext(fs.readFileSync('dashboard/field-sync.js','utf8'),context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function settle(){for(let i=0;i<60;i++)await tick();}
(async()=>{
 await settle();assert.equal(calls.length,0,'default opt-out must not access network');
 el('syncToggle').checked=true;await el('syncToggle').handlers.change();
 await settle();
 assert.equal(calls.filter(x=>x.path==='/api/private-intake/prepare').length,1);
 assert.equal(storage['habu-field-sync-v1'].receipts.get(session.id).state,'ARCHIVED');
 assert.equal(el('syncConfirm').disabled,false);
 await el('syncConfirm').handlers.click();await settle();
 assert.equal(storage['habu-field-sync-v1'].receipts.get(session.id).state,'APPLIED');
 assert.equal(revision,1);assert.match(el('syncState').textContent,/読み戻し成功/);
 const posts=calls.filter(x=>x.method==='POST').length;
 await context.window.HabuFieldSync.notifyStop();await settle();
 assert.equal(calls.filter(x=>x.method==='POST').length,posts,'repeated sync must not resubmit');
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-'],input=js,cwd=ROOT,capture_output=True,text=True,
                              encoding='utf-8',timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
