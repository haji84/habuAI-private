"""Run the real intake controller through the real service-worker fetch path."""
import shutil
import subprocess
from pathlib import Path
import unittest

from test_field_offline import SW_SIM

ROOT=Path(__file__).resolve().parents[1]
PREFIX=SW_SIM.split('async function run(){',1)[0]
SCENARIO=r"""
const mode=process.argv[1];
let serverSummary={schema_version:'habu-capture-dashboard-v2',asof:'2026-10-24',total:249,nights:[]};
FakeResponse.prototype.json=async function(){return JSON.parse(this.textBody)};
class Element {
 constructor(){this.children=[];this.listeners={};this.value='';this.files=[];this.disabled=false;}
 append(...items){this.children.push(...items)}
 replaceChildren(...items){this.children=[...items]}
 addEventListener(name,fn){this.listeners[name]=fn}
 setAttribute(){} click(){} remove(){}
}
async function main(){
 const sw={URL,TextDecoder,Request:FakeRequest,Response:FakeResponse,Promise,Set,caches:api,
  self:{registration:{scope:base},clients:{claim:async()=>{}},skipWaiting:async()=>{},
   addEventListener:(name,cb)=>registered[name]=cb},
  fetch:async req=>{
   if(offline)throw Error('network offline');
   const path=new URL(req.url||req).pathname;
   const htmlFile={'/':'/index.html','/field':'/field.html','/intake':'/intake.html'}[path]||path;
   const json=path.endsWith('.json');
   const type=json?'application/json':path.endsWith('.js')?'application/javascript':
    path.endsWith('.webmanifest')?'application/manifest+json':path.endsWith('.png')?'image/png':'text/html';
   const body=json?JSON.stringify(serverSummary):htmlFile.endsWith('.html')?
    fs.readFileSync('dashboard'+htmlFile,'utf8'):'ASSET '+path;
   return new FakeResponse(body,{url:req.url||req,headers:{'content-type':type}});
  }};
 vm.runInNewContext(script,sw,{filename:'sw.js'});
 let install;registered.install({waitUntil(p){install=p}});await install;
 let active;registered.activate({waitUntil(p){active=p}});await active;
 await respond('data/capture_summary.json'); // Deliberately retain an old offline fallback.
 if(mode==='offline_initial')offline=true;
 const elements=new Map();const element=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id)};
 element('export').disabled=true;
 const blobs=[];
 let fetches=0;
 const document={getElementById:element,createElement:()=>new Element(),body:new Element()};
 const ui=vm.createContext({document,HabuLogIntake:require('./dashboard/intake-core.js'),
  crypto:require('node:crypto').webcrypto,TextEncoder,TextDecoder,Blob,console,
  URL:{createObjectURL:blob=>{blobs.push(blob);return 'blob:test'},revokeObjectURL(){}},
  setTimeout:fn=>fn(),
  fetch:async url=>{
   const response=await respond(String(url).replace(/^\.\//,''));fetches++;
   if(mode==='changed_input'&&fetches===3)element('clear').listeners.click();
   return response;
  }});
 const html=fs.readFileSync('dashboard/intake.html','utf8');
 const source=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m=>m[1]).find(s=>s.includes('async function loadSummary'));
 assert(source,'actual intake controller absent');
 vm.runInContext(source,ui,{filename:'intake.html'});
 for(let i=0;i<4;i++)await new Promise(resolve=>setImmediate(resolve));
 element('pasted').value='ハブログ\n2026/10/27 20:10\n捕獲\nハブ';
 await element('analyze').listeners.click();
 const row=element('rows').children[0];assert(row,'actual parser produced no night');
 const number=row.children[4].children[0];number.value='2';number.listeners.input();
 const searched=row.children[5].children[0].children[0];searched.checked=true;searched.onchange();
 const approved=row.children[6].children[0].children[0];approved.checked=true;approved.onchange();
 if(mode==='offline_before_export')offline=true;
 if(mode==='changed_baseline')serverSummary={...serverSummary,asof:'2026-10-27',
  nights:[{night:'2026-10-27',count:2,effort_confirmed:true}]};
 await element('export').listeners.click();
 if(mode==='online'||mode.startsWith('online_')){
  assert.equal(blobs.length,1);
  const batch=JSON.parse(await blobs[0].text());
  assert.equal(batch.baseline_asof,'2026-10-24');assert.equal(batch.files.length,1);
  assert.equal(batch.files[0].content.capture_count,2);
  assert.equal(batch.counts_are_owner_confirmed_not_scientific_labels,true);
  if(mode==='online_edit_again'){
   number.value='5';number.listeners.input();await element('export').listeners.click();
   assert.equal(blobs.length,2);
   assert.equal(JSON.parse(await blobs[1].text()).files[0].content.capture_count,5,
    'visible edited quantity must be the second export quantity');
  }
  if(mode==='online_uncheck_again'){
   searched.checked=false;searched.onchange();
   assert.equal(element('export').disabled,true,'revoked owner confirmation must disable export');
   await element('export').listeners.click();assert.equal(blobs.length,1);
  }
 }else{
  assert.equal(blobs.length,0,'stale/missing baseline must not produce an intake package');
  assert.equal(element('export').disabled,true,'failed freshness must disable export');
 }
 console.log('INTAKE_FRESH_E2E_PASS '+mode);
}
main().catch(error=>{console.error(error);process.exit(1)});
"""


@unittest.skipUnless(shutil.which('node'),'Node.js required for real controller/SW integration')
class IntakeFreshSummaryTests(unittest.TestCase):
    def check(self,mode):
        result=subprocess.run(['node','-e',PREFIX+SCENARIO,mode],cwd=ROOT,
            capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_cached_summary_cannot_certify_new_package_while_offline(self):self.check('offline_initial')
    def test_online_boot_does_not_allow_later_offline_export(self):self.check('offline_before_export')
    def test_intervening_server_registration_requires_recomparison(self):self.check('changed_baseline')
    def test_input_reset_during_fresh_fetch_cannot_export_the_old_confirmation(self):self.check('changed_input')
    def test_live_server_baseline_still_produces_aggregate_only_package(self):self.check('online')
    def test_repeated_export_uses_the_current_visible_owner_quantity(self):self.check('online_edit_again')
    def test_repeated_export_respects_revoked_owner_confirmation(self):self.check('online_uncheck_again')


if __name__=='__main__':unittest.main()
