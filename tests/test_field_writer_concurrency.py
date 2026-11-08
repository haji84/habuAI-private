"""Two real field controllers sharing a serialized, transactional IDB boundary.

Only synthetic GPS/events are used. The fake implements IDB's readwrite
serialization, request callbacks, commit/abort, and structured-clone boundary;
the controller, session logic, UI handlers and exported backups are real.
"""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
HARNESS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const core=require('./dashboard/field-core.js');
const source=fs.readFileSync('./dashboard/field-app.js','utf8');
const copy=x=>x===undefined?undefined:structuredClone(x);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function database(initial){
 const rows=new Map(initial.map(x=>[x.id,copy(x)])),queue=[];
 const state={rows,paused:false,active:false,failNext:false};
 function pump(){
  if(state.active||!queue.length||state.paused)return;
  state.active=true;const tx=queue.shift(),local=new Map([...rows].map(([k,v])=>[k,copy(v)]));
  let aborted=false,operations=tx.operations;
  tx.abort=()=>{aborted=true;};
  const finish=()=>{
   if(aborted){if(tx.onabort)tx.onabort();}
   else{if(tx.mode==='readwrite'){rows.clear();for(const [k,v] of local)rows.set(k,v);}
    if(tx.oncomplete)tx.oncomplete();}
   state.active=false;setImmediate(pump);
  };
  const next=()=>setImmediate(()=>{
   if(aborted||!operations.length){finish();return;}
   const op=operations.shift();
   if(op.kind==='get')op.req.result=copy(local.get(op.key));
   if(op.kind==='getAll')op.req.result=[...local.values()].map(copy);
   if(op.kind==='put'){
    local.set(op.value.id,copy(op.value));
    if(state.failNext){state.failNext=false;aborted=true;tx.error=Error('synthetic transaction abort');}
   }
   if(!aborted&&op.req.onsuccess)op.req.onsuccess();
   next();
  });next();
 }
 const db={transaction(store,mode){
  assert.equal(store,'sessions');const tx={mode,operations:[]};
  tx.objectStore=()=>({get(key){const req={};tx.operations.push({kind:'get',key,req});return req;},
   getAll(){const req={};tx.operations.push({kind:'getAll',req});return req;},
   put(value){const req={};tx.operations.push({kind:'put',value:copy(value),req});return req;}});
  queue.push(tx);setImmediate(pump);return tx;
 }};
 state.resume=()=>{state.paused=false;pump();};
 state.idb={open(){const req={result:db};setImmediate(()=>req.onsuccess());return req;}};
 state.idle=async()=>{for(let stable=0;stable<4;){await tick();stable=!state.active&&!queue.length?stable+1:0;}};
 return state;
}
function fixture(withPoint=true){
 const s=core.createSession('synthetic-session-0000001','2026-10-27T12:00:00Z');
 if(withPoint)core.recordPoint(s,{latitude:0,longitude:0,accuracy:5},'2026-10-27T12:00:01Z');
 core.event(s,{id:'original-event-000001',type:'sighting',species:'synthetic',count:1,owner:'self',
  time:'2026-10-27T12:00:02Z',note:'original raw string'});
 return s;
}
async function controller(shared){
 const elements=new Map(),windowEvents={},documentEvents={},blobs=new Map(),downloads=[];
 let fix,error,cleared=0;
 const element=()=>({dataset:{},handlers:{},value:'',disabled:false,hidden:false,
  addEventListener(n,f){this.handlers[n]=f;},replaceChildren(){},append(){},remove(){},click(){}});
 const get=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
 const context={console,Blob,Promise,Set,Map,Date,JSON,Math,Number,Error,TextEncoder,
  setTimeout(fn,ms){if(ms!==10000)return setTimeout(fn,ms);},clearTimeout,
  indexedDB:shared.idb,crypto:{randomUUID:()=>require('node:crypto').randomUUID()},
  confirm:()=>true,URL:{createObjectURL(blob){const key='blob:'+blobs.size;blobs.set(key,blob);return key;},revokeObjectURL(){}},
  document:{body:{append(a){downloads.push(a);}},getElementById:get,
   createElement(){return element();},addEventListener(n,f){documentEvents[n]=f;},visibilityState:'visible'},
  navigator:{storage:{persist:async()=>true},geolocation:{watchPosition(f,e){fix=f;error=e;return 1;},clearWatch(){cleared++;}}},
  window:{HabuFieldCore:core,indexedDB:shared.idb,isSecureContext:true,addEventListener(n,f){windowEvents[n]=f;}}};
 vm.runInNewContext(source,context,{filename:'field-app.js'});await shared.idle();
 get('species').value='synthetic';get('count').value='1';get('type').value='sighting';get('owner').value='self';
 return {get,context,cleared:()=>cleared,
  click:async id=>{const p=get(id).handlers.click();if(p)await p;},
  fix(lat,offset=0){fix({coords:{latitude:lat,longitude:0,accuracy:5},timestamp:Date.now()+offset});},
  error(){error({code:2});},
  pagehide(){windowEvents.pagehide();},
  hidden(){context.document.visibilityState='hidden';documentEvents.visibilitychange();},
  visible(){context.document.visibilityState='visible';documentEvents.visibilitychange();},
  async select(id){await get('saved').handlers.change({target:{value:id}});},
  async backup(){await this.click('backup');return JSON.parse(await blobs.get(downloads.at(-1).href).text());},
  async gpx(){await this.click('gpxExport');return await blobs.get(downloads.at(-1).href).text();}};
}
"""


@unittest.skipUnless(NODE, "node required")
class FieldWriterConcurrencyTests(unittest.TestCase):
    def run_js(self, body):
        result = subprocess.run([NODE, "-"], input=HARNESS + "\n(async()=>{\n" + body +
                                "\n})().catch(e=>{console.error(e);process.exitCode=1;});\n",
                                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_two_actual_controllers_preserve_winner_and_loser_raw_points(self):
        self.run_js(r"""
const seed=fixture(),shared=database([seed]),a=await controller(shared),b=await controller(shared);
shared.paused=true;await a.click('gpsStart');await b.click('gpsStart');a.fix(.001);b.fix(.002,1000);
shared.resume();await shared.idle();const saved=shared.rows.get(seed.id);
assert.equal(b.get('state').dataset.kind,'bad');const backup=await b.backup();
assert.deepEqual(saved.points.map(p=>p.lat),[0,.001],'stale tab must not replace the first tab point');
assert.deepEqual(backup.points.map(p=>p.lat),[0,.002],'unsaved losing-tab GPS must remain exportable');
assert.deepEqual(saved.events,seed.events);assert.deepEqual(backup.events,seed.events);
assert.equal(a.cleared(),0);assert.equal(b.cleared(),1);
assert.equal(b.get('gpsStart').disabled,true);assert.equal(b.get('add').disabled,true);
assert.equal(b.get('backup').disabled,false);assert.equal(b.get('gpxExport').disabled,false);
assert((await b.gpx()).includes('lat="0.002"'));
""")

    def test_same_baseline_concurrent_writes_have_only_one_winner(self):
        self.run_js(r"""
const seed=fixture(false),shared=database([seed]),a=await controller(shared),b=await controller(shared);
await a.click('gpsStart');await b.click('gpsStart');a.fix(.001);b.fix(.002,1000);await shared.idle();
assert.deepEqual(shared.rows.get(seed.id).points.map(p=>p.lat),[.001]);
assert.equal(a.cleared()+b.cleared(),1);assert.equal(shared.rows.get(seed.id).revision,seed.revision+1);
""")

    def test_stale_observation_cannot_replace_saved_event_or_raw_point(self):
        self.run_js(r"""
const seed=fixture(),shared=database([seed]),a=await controller(shared),b=await controller(shared);
a.get('note').value='first observation';await a.click('add');await shared.idle();
const winner=copy(shared.rows.get(seed.id));b.get('note').value='second observation';await b.click('add');await shared.idle();
assert.deepEqual(shared.rows.get(seed.id),winner);
assert.equal((await b.backup()).events.at(-1).note,'second observation');
assert.equal(b.get('add').disabled,true);assert.equal(b.get('batchExport').disabled,true);
""")

    def test_queued_saves_in_one_tab_advance_the_observed_baseline_after_commit(self):
        self.run_js(r"""
const seed=fixture(false),shared=database([seed]),a=await controller(shared);await a.click('gpsStart');
a.fix(.001);a.fix(.002,1000);await shared.idle();
assert.deepEqual(shared.rows.get(seed.id).points.map(p=>p.lat),[.001,.002]);
assert.equal(a.cleared(),0);assert.equal(a.get('add').disabled,false);
assert.equal(shared.rows.get(seed.id).revision,seed.revision+2);
""")

    def test_legacy_missing_and_zero_revisions_are_writable_without_losing_other_raw_fields(self):
        self.run_js(r"""
for(const revision of [undefined,0]){
 const seed=fixture(false);if(revision===undefined)delete seed.revision;else seed.revision=revision;
 const shared=database([seed]),a=await controller(shared);await a.click('gpsStart');a.fix(.001);await shared.idle();
 assert.equal(shared.rows.get(seed.id).revision,1);assert.deepEqual(shared.rows.get(seed.id).events,seed.events);
 assert.equal(a.cleared(),0);
}
""")

    def test_transaction_abort_keeps_database_and_unsaved_backup_and_freezes_callbacks(self):
        self.run_js(r"""
const seed=fixture(false),shared=database([seed]),a=await controller(shared);await a.click('gpsStart');
shared.failNext=true;a.fix(.001);await shared.idle();const unsaved=await a.backup();
assert.deepEqual(shared.rows.get(seed.id),seed);assert.deepEqual(unsaved.points.map(p=>p.lat),[.001]);
assert.equal(a.cleared(),1);assert.equal(a.get('add').disabled,true);assert.equal(a.get('backup').disabled,false);
a.fix(.002,1000);a.error();a.hidden();a.pagehide();await a.click('gpsStop');await shared.idle();
assert.deepEqual(await a.backup(),unsaved,'late callbacks must not mutate the frozen recovery copy');
assert.deepEqual(shared.rows.get(seed.id),seed);
await a.select(seed.id);assert.deepEqual(await a.backup(),unsaved,'reselect must not discard unsaved raw data');
""")

    def test_invalid_or_pre_session_gps_still_does_not_enter_database(self):
        self.run_js(r"""
const seed=fixture(false),shared=database([seed]),a=await controller(shared);await a.click('gpsStart');
a.fix(1000);a.fix(.001,-Date.now());await shared.idle();assert.deepEqual(shared.rows.get(seed.id),seed);
assert.equal((await a.backup()).points.length,0);
""")

    def test_two_restore_prechecks_cannot_overwrite_a_newly_created_same_id(self):
        self.run_js(r"""
const first=fixture(),second=copy(first);core.stop(first,'2026-10-27T13:00:00Z');
core.stop(second,'2026-10-27T13:00:00Z');second.points[0].lat=.002;
const shared=database([]),a=await controller(shared),b=await controller(shared);
const restore=(tab,row)=>tab.get('restore').handlers.change({target:{value:'synthetic',
 files:[{size:100,text:async()=>JSON.stringify(row)}]}});
await Promise.all([restore(a,first),restore(b,second)]);await shared.idle();
assert.deepEqual(shared.rows.get(first.id).points,first.points);
assert.deepEqual(shared.rows.get(first.id).events,first.events);
assert.deepEqual((await b.backup()).points,second.points);
assert.equal(b.get('start').disabled,true);assert.equal(b.get('restore').disabled,true);
""")

    def test_aborted_transaction_does_not_advance_or_run_already_queued_writes(self):
        self.run_js(r"""
const seed=fixture(false),shared=database([seed]),a=await controller(shared);await a.click('gpsStart');
shared.failNext=true;a.fix(.001);a.fix(.002,1000);await shared.idle();
assert.deepEqual(shared.rows.get(seed.id),seed);
assert.deepEqual((await a.backup()).points.map(p=>p.lat),[.001,.002]);
assert.equal(a.cleared(),1);assert.equal(a.get('add').disabled,true);
""")

    def test_visibility_return_preserves_the_unsaved_recovery_message(self):
        self.run_js(r"""
const shared=database([fixture(false)]),a=await controller(shared);await a.click('gpsStart');
shared.failNext=true;a.fix(.001);await shared.idle();const message=a.get('state').textContent;
assert.equal(a.get('state').dataset.kind,'bad');a.hidden();a.visible();await shared.idle();
assert.equal(a.get('state').textContent,message,'visibility return must retain the recovery instructions');
assert.equal(a.get('state').dataset.kind,'bad');assert.equal(a.get('gpsStart').disabled,true);
""")


if __name__ == "__main__":
    unittest.main()
