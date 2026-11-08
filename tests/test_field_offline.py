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
function streamBody(text){let done=false;return {getReader(){return {async read(){if(done)return {done:true};done=true;return {done:false,value:new TextEncoder().encode(text)};},async cancel(){done=true;},releaseLock(){}};}};}
class FakeResponse {
 constructor(body,{ok=true,redirected=false,type='basic',headers={},url='',status=200}={}){
  this.textBody=body;this.body=streamBody(body);this.url=url;this.status=status;this.ok=ok;this.redirected=redirected;this.type=type;
  this.headers={get:(key)=>headers[key.toLowerCase()]||null};
 }
 clone(){return new FakeResponse(this.textBody,{ok:this.ok,redirected:this.redirected,type:this.type,
  url:this.url,status:this.status,headers:{'content-type':this.headers.get('content-type')}});}
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
  URL,TextDecoder,Request:FakeRequest,Response:FakeResponse,Promise,Set,caches:api,
  self:{registration:{scope:base},clients:{claim:async()=>{}},skipWaiting:async()=>{},
    addEventListener:(name,cb)=>registered[name]=cb},
  fetch:async (req)=>{
   if(offline)throw Error('network offline');
   const path=new URL(req.url||req).pathname;
   const htmlFile={'/':'/index.html','/field':'/field.html','/intake':'/intake.html'}[path]||path;
   let ct=path.endsWith('.js')?'application/javascript':
     htmlFile.endsWith('.html')||path==='/'?'text/html':
     path.endsWith('.json')?'application/json':
     path.endsWith('.webmanifest')?'application/manifest+json':'image/png';
   return new FakeResponse(htmlFile.endsWith('.html')?fs.readFileSync('dashboard'+htmlFile,'utf8'):'ASSET '+htmlFile,{url:req.url||req,headers:{'content-type':ct}});
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
 assert((await respond('field.html')).textBody.includes('field-core.js'));
 assert((await respond('field-core.js')).textBody.includes('/field-core.js'));
 assert((await respond('field-app.js')).textBody.includes('/field-app.js'));
 assert((await respond('intake.html')).textBody.includes('intake-core.js'));
 assert((await respond('index.html')).textBody.includes('snapshot'));
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
 assert((await cached).textBody.includes('field-core.js'));
 // Access redirects during installation must never be cached as the field app.
 buckets.clear();offline=false;
 context.fetch=async(req)=>{
  const path=new URL(req.url||req).pathname;
  if(path.endsWith('field-app.js'))return new FakeResponse('LOGIN',{headers:{'content-type':'text/html'},redirected:true});
  return new FakeResponse(['/','/field','/intake'].includes(path)?fs.readFileSync('dashboard'+({'/':'/index.html','/field':'/field.html','/intake':'/intake.html'}[path]),'utf8'):'OK',{url:req.url||req,headers:{'content-type':path.endsWith('.js')?'application/javascript':path.endsWith('.html')||['/','/field','/intake'].includes(path)?'text/html':'application/json'}});
 };
 let failed;
 registered.install({waitUntil(p){failed=p;}});
 await assert.rejects(failed,/Offline shell requires authenticated/);
 assert.equal((await api.keys()).length,0);
 console.log('OFFLINE_FIELD_SW_PASS');
}
run().catch(e=>{console.error(e);process.exit(1);});
"""


CANONICAL_SW_SIM=r'''
const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const base='https://example.test/app/',handlers={},buckets=new Map(),calls=[];
let mode='canonical',offline=false;
class Req{constructor(url,opts){this.url=String(url);this.method='GET';this.opts=opts;}}
function streamBody(text){let done=false;return {getReader(){return {async read(){if(done)return {done:true};done=true;return {done:false,value:new TextEncoder().encode(text)};},async cancel(){done=true;},releaseLock(){}};}};}
class Res{
 constructor(body,url,status=200,type='basic',redirected=false,ct='text/html'){
  Object.assign(this,{textBody:body,url,status,type,redirected,ok:status>=200&&status<300});this.body=streamBody(body);this.headers={get:()=>ct};this.ct=ct;}
 clone(){return new Res(this.textBody,this.url,this.status,this.type,this.redirected,this.ct);}
 async text(){return this.textBody;}
 static error(){return new Res('',base,0,'error');}
}
function body(path){
 const name=path.endsWith('/field')||path.endsWith('/field.html')?'field.html':
  path.endsWith('/intake')||path.endsWith('/intake.html')?'intake.html':
  path.endsWith('/')||path.endsWith('/index.html')?'index.html':null;
 return name?fs.readFileSync('dashboard/'+name,'utf8'):'STATIC_ASSET';
}
const api={open:async name=>{
 if(!buckets.has(name))buckets.set(name,new Map());const b=buckets.get(name);
 return {put:async(req,res)=>b.set(req.url||req,res.clone()),match:async req=>b.get(req.url||req)};
},keys:async()=>[...buckets.keys()],delete:async name=>buckets.delete(name),match:async(req,opts)=>{
 const key=req.url||req;for(const [name,b] of buckets)if(!opts?.cacheName||name===opts.cacheName){if(b.has(key))return b.get(key);}
}};
const context={URL,TextDecoder,Request:Req,Response:Res,Set,Map,Promise,caches:api,
 self:{registration:{scope:base},clients:{claim:async()=>{}},skipWaiting:async()=>{},addEventListener:(k,f)=>handlers[k]=f},
 fetch:async req=>{
  calls.push(req.url);if(offline)throw Error('offline');const u=new URL(req.url),path=u.pathname;
  const canonical=path.endsWith('/field')||path.endsWith('/intake');
  if(mode==='legacy'&&canonical)return new Res('missing',req.url,404);
  if(mode==='canonical'&&path.endsWith('.html'))return new Res('redirect',req.url,200,'basic',true);
  if(path.endsWith('/field')){
   if(mode==='access')return new Res('LOGIN',base+'cdn-cgi/access/login',200,'basic',true);
   if(mode==='crossorigin')return new Res(body(path),'https://evil.test/field');
   if(mode==='opaque')return new Res(body(path),req.url,200,'opaque');
   if(mode==='fallback-dashboard')return new Res(body('/'),req.url);
   if(mode==='login200')return new Res('<html>Access login</html>',req.url);
  }
  return new Res(body(path),req.url,200,'basic',false,path.endsWith('.js')?'application/javascript':
   canonical||path.endsWith('.html')||path.endsWith('/')?'text/html':path.endsWith('.json')?'application/json':'image/png');
 }};
vm.runInNewContext(fs.readFileSync('dashboard/sw.js','utf8'),context);
async function install(){let done;handlers.install({waitUntil:p=>done=p});await done;}
async function request(path){let p;handlers.fetch({request:new Req(base+path),respondWith:x=>p=x,waitUntil:()=>{}});assert(p,'canonical request must be handled');return await p;}
'''

PREPARATION_SIM=r'''
const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const full=fs.readFileSync('dashboard/field-app.js','utf8');
const code=full.slice(full.indexOf('let offlineShellReady='),full.indexOf("window.addEventListener('online'"));
const timers=new Map(),ports=[],display={dataset:{},textContent:'checking'};let timerId=0;
let register=()=>Promise.resolve({active:worker}),ready=Promise.resolve({active:null});
let send=(msg,port)=>port.peer.onmessage?.({data:{type:'HABU_FIELD_OFFLINE_STATUS',ready:true}});
const worker={postMessage(msg,ps){send(msg,ps[0]);}};
class Channel{constructor(){
 const a={closed:false,close(){this.closed=true;}},b={closed:false,close(){this.closed=true;}};
 a.peer=b;b.peer=a;this.port1=a;this.port2=b;ports.push(a,b);
}}
const sw={register:(...args)=>register(...args),get ready(){return ready;}};
const ctx={Promise,Error,MessageChannel:Channel,navigator:{serviceWorker:sw,onLine:true},window:{isSecureContext:true},
 $:()=>display,setTimeout:(fn,ms)=>{assert(ms>0&&ms<=30000);timers.set(++timerId,fn);return timerId;},clearTimeout:id=>timers.delete(id)};
vm.runInNewContext(code+'\nglobalThis.prepare=prepareOfflineShell;globalThis.isReady=()=>offlineShellReady;',ctx);
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
function expire(){for(const [id,fn] of [...timers]){timers.delete(id);fn();}}
'''


class OfflineFieldTests(unittest.TestCase):
    def test_real_response_clone_over_limit_cannot_wait_for_unread_tee_branch(self):
        self.node_control(r'''
const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const ctx={URL,TextDecoder,Request,Response,self:{registration:{scope:'https://example.test/'},addEventListener(){}}};
vm.runInNewContext(fs.readFileSync('dashboard/sw.js','utf8')+'\nglobalThis.checkRole=htmlRoleMatches;',ctx);
(async()=>{const html=fs.readFileSync('dashboard/field.html','utf8'),valid=new Response(html);
 assert.equal(await ctx.checkRole(valid,'./field.html'),true);assert.equal(await valid.text(),html);
 const stream=new ReadableStream({pull(c){c.enqueue(new Uint8Array(1024*1024));}});
 const response=new Response(stream);let timer;
 try{const result=await Promise.race([ctx.checkRole(response,'./field.html'),new Promise(resolve=>timer=setTimeout(()=>resolve('STALLED'),1000))]);
  assert.equal(result,false);
 }finally{clearTimeout(timer);response.body.cancel().catch(()=>{});}
 console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_evicted_intake_html_is_not_reported_as_complete_offline_shell(self):
        self.node_control(CANONICAL_SW_SIM+r'''
(async()=>{await install();for(const bucket of buckets.values())bucket.delete(base+'intake.html');
 let reply,pending;handlers.message({data:{type:'HABU_FIELD_OFFLINE_STATUS'},
 ports:[{postMessage:v=>reply=v}],waitUntil:p=>pending=p});await pending;
 assert.equal(reply.ready,false);console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_only_exact_404_can_use_fixed_legacy_fallback(self):
        self.node_control(CANONICAL_SW_SIM+r'''
(async()=>{const normal=context.fetch;
 for(const bad of ['401','403','500','redirect404','opaque404','cors404','foreign404','mime','wrongpath']){
  buckets.clear();calls.length=0;
  context.fetch=async req=>{assert.equal(req.opts.redirect,'error');
   if(!req.url.endsWith('/field'))return normal(req);calls.push(req.url);
   if(['401','403','500'].includes(bad))return new Res('blocked',req.url,Number(bad));
   if(bad==='redirect404')return new Res('blocked',req.url,404,'basic',true);
   if(bad==='opaque404'||bad==='cors404')return new Res('blocked',req.url,404,bad.slice(0,-3));
   if(bad==='foreign404')return new Res('blocked','https://evil.test/field',404);
   if(bad==='wrongpath')return new Res(body('/field'),base+'intake');
   return new Res(body('/field'),req.url,200,'basic',false,'text/plain');
  };
  await assert.rejects(install());assert(!calls.includes(base+'field.html'));assert.equal(buckets.size,0);
 }console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_html_stream_cap_cancels_reader_and_does_not_cache(self):
        self.node_control(CANONICAL_SW_SIM+r'''
(async()=>{let cancelled=false,released=false,reads=0;const normal=context.fetch;
 context.fetch=async req=>{
  if(!req.url.endsWith('/field'))return normal(req);
  const r=new Res('',req.url);r.clone=()=>({body:{getReader:()=>({
   async read(){reads++;return {done:false,value:new Uint8Array(1024*1024)};},
   async cancel(){cancelled=true;},releaseLock(){released=true;}
  })}});return r;
 };
 await assert.rejects(install());assert.equal(reads,3);assert(cancelled&&released);assert.equal(buckets.size,0);
 console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_one_deadline_spans_register_ready_status_and_late_reply(self):
        self.node_control(PREPARATION_SIM+r'''
(async()=>{let resolveRegister,resolveReady,late;
 register=()=>new Promise(r=>resolveRegister=r);ready=new Promise(r=>resolveReady=r);
 const pending=ctx.prepare();await flush();const firstTimer=[...timers.keys()][0];assert.equal(timers.size,1);
 resolveRegister({active:worker});await flush();assert.equal([...timers.keys()][0],firstTimer);
 send=(m,p)=>{late=p.peer.onmessage;};resolveReady({active:worker});await flush();
 assert.equal(timers.size,1);assert.equal([...timers.keys()][0],firstTimer);
 expire();await pending;assert.equal(ctx.isReady(),false);assert(ports.every(p=>p.closed));
 late({data:{type:'HABU_FIELD_OFFLINE_STATUS',ready:true}});assert.equal(ctx.isReady(),false);
 assert.equal(timers.size,0);console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_superseded_status_reply_cannot_replace_latest_false_status(self):
        self.node_control(PREPARATION_SIM+r'''
(async()=>{ready=Promise.resolve({active:worker});let oldReply;
 send=(m,p)=>oldReply=p.peer.onmessage;const old=ctx.prepare();await flush();
 send=(m,p)=>p.peer.onmessage({data:{type:'HABU_FIELD_OFFLINE_STATUS',ready:false}});
 await ctx.prepare();await old;oldReply({data:{type:'HABU_FIELD_OFFLINE_STATUS',ready:true}});
 assert.equal(ctx.isReady(),false);assert(ports.every(p=>p.closed));assert.equal(timers.size,0);
 console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def node_control(self,script):
        if not shutil.which('node'):self.skipTest('Node.js required')
        proc=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn('CONTROL_PASS',proc.stdout)

    def test_canonical_network_shell_and_both_offline_aliases(self):
        self.node_control(CANONICAL_SW_SIM+r'''
(async()=>{await install();offline=true;
 for(const path of ['field','field.html'])assert((await request(path)).textBody.includes('field-core.js'));
 for(const path of ['intake','intake.html'])assert((await request(path)).textBody.includes('intake-core.js'));
 assert(!calls.some(x=>x.endsWith('.html')),'canonical host must not fetch redirecting HTML names');
 assert.equal((await request('field')).textBody,(await request('field.html')).textBody);
 console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_legacy_404_fallback_binds_identical_known_alias_content(self):
        self.node_control(CANONICAL_SW_SIM+r'''
(async()=>{mode='legacy';await install();offline=true;
 assert(calls.includes(base+'field')&&calls.includes(base+'field.html'));
 assert.equal((await request('field')).textBody,(await request('field.html')).textBody);
 assert.equal((await request('intake')).textBody,(await request('intake.html')).textBody);
 console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_access_crossorigin_opaque_and_dashboard_substitution_fail_closed(self):
        self.node_control(CANONICAL_SW_SIM+r'''
(async()=>{for(const bad of ['access','crossorigin','opaque','fallback-dashboard','login200']){
 mode=bad;buckets.clear();calls.length=0;await assert.rejects(install());
 assert(!calls.includes(base+'field.html'),'Access/error content must not trigger legacy fallback');
 assert.equal(buckets.size,0);
 }console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_register_ready_and_status_all_have_bounded_wait_and_retry(self):
        self.node_control(PREPARATION_SIM+r'''
(async()=>{for(const stage of ['register','ready','status']){
 register=()=>stage==='register'?new Promise(()=>{}):Promise.resolve({active:worker});
 ready=stage==='ready'?new Promise(()=>{}):Promise.resolve({active:worker});
 send=()=>{};let settled=false;const p=ctx.prepare().then(()=>settled=true);await flush();expire();await flush();
 assert(settled,stage+' cannot wait forever');assert.equal(ctx.isReady(),false);assert.notEqual(display.textContent,'checking');
 await p;assert.equal(timers.size,0);assert(ports.every(p=>p.closed));
 }register=()=>Promise.resolve({active:worker});ready=Promise.resolve({active:worker});
 send=(m,p)=>p.peer.onmessage?.({data:{type:'HABU_FIELD_OFFLINE_STATUS',ready:true}});
 await ctx.prepare();assert.equal(ctx.isReady(),true);assert.equal(timers.size,0);assert(ports.every(p=>p.closed));
 console.log('CONTROL_PASS');})().catch(e=>{console.error(e);process.exitCode=1;});
''')

    def test_stale_attempt_cannot_clear_new_success_and_post_failure_closes_ports(self):
        self.node_control(PREPARATION_SIM+r'''
(async()=>{let oldResolve;ready=new Promise(r=>oldResolve=r);
 const old=ctx.prepare();await flush();ready=Promise.resolve({active:worker});
 await ctx.prepare();assert.equal(ctx.isReady(),true);oldResolve({active:{postMessage(){throw Error('old worker');}}});
 await old;await flush();expire();await flush();assert.equal(ctx.isReady(),true);assert.equal(timers.size,0);
 send=()=>{throw Error('post failed');};await ctx.prepare();assert.equal(ctx.isReady(),false);
 assert(ports.every(p=>p.closed));assert.equal(timers.size,0);console.log('CONTROL_PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
''')


    def run_node(self, script):
        if not shutil.which('node'):
            self.skipTest('Node.js required')
        result = subprocess.run(['node', '-e', script], cwd=ROOT,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pages_pretty_html_redirects_do_not_abort_shell_installation(self):
        harness = SW_SIM.replace(
            "   let ct=path.endsWith('.js')?",
            "   if(path.endsWith('.html'))return new FakeResponse('CANONICAL_HTML',"
            "{redirected:true,headers:{'content-type':'text/html'}});\n"
            "   let ct=path.endsWith('.js')?", 1)
        self.run_node(harness)

    def test_pretty_field_and_intake_paths_use_their_own_offline_pages(self):
        harness = SW_SIM.replace(
            " offline=true;\n assert((await respond('field.html'))",
            " offline=true;\n"
            " assert.equal((await respond('field')).textBody,fs.readFileSync('dashboard/field.html','utf8'));\n"
            " assert.equal((await respond('intake')).textBody,fs.readFileSync('dashboard/intake.html','utf8'));\n"
            " assert.equal((await respond('field?view=synthetic')).textBody,fs.readFileSync('dashboard/field.html','utf8'));\n"
            " assert((await respond('field.html'))", 1)
        self.run_node(harness)

    def run_offline_preparation(self, phase):
        self.run_node(r'''
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('dashboard/field-app.js','utf8');
const start=source.indexOf('async function prepareOfflineShell(){');
const end=source.indexOf("\nwindow.addEventListener('online'",start);
assert(start>=0&&end>start,'Find the actual field offline preparation entry point');
const entry=source.slice(start,end);
const phase=PHASE;
const never=new Promise(()=>{});
const timers=new Map();let nextTimer=0;let settled=false;const messages=[];const ports=[];
class Channel {
 constructor(){
  this.port1={onmessage:null,closed:false,close(){this.closed=true;}};
  this.port2={closed:false,close(){this.closed=true;},deliver:data=>{
   if(!this.port1.closed&&this.port1.onmessage)this.port1.onmessage({data});
  }};
  ports.push(this.port1,this.port2);
 }
}
const worker={postMessage(message,ports){
 assert.equal(message.type,'HABU_FIELD_OFFLINE_STATUS');
 if(phase==='postMessageThrow')throw Error('synthetic postMessage failure');
 if(phase==='statusTimeout')return;
 ports[0].deliver({type:'HABU_FIELD_OFFLINE_STATUS',ready:true});
}};
const ctx={window:{isSecureContext:true},offlineShellReady:false,offlinePreparation:null,
 navigator:{serviceWorker:{
  register:()=>phase==='register'?never:Promise.resolve({active:worker}),
  ready:phase==='ready'?never:Promise.resolve({active:worker})}},
 setTimeout(fn,ms){const id=++nextTimer;timers.set(id,{fn,ms});return id;},
 clearTimeout(id){timers.delete(id);},MessageChannel:Channel,
 showOfflineState(message,kind){messages.push({message,kind});},
 connectivityStatus(){messages.push({kind:ctx.offlineShellReady?'ok':'warn'});}
};
async function run(){
 const task=vm.runInNewContext('('+entry+')()',ctx);
 task.then(()=>{settled=true;},()=>{settled=true;});
 for(let i=0;i<20;i++)await Promise.resolve();
 if(['register','ready','statusTimeout'].includes(phase)){
  const pending=[...timers.entries()].find(([,t])=>t.ms>0&&t.ms<=10000);
  assert(pending,'Startup must arm a deadline before waiting on registration/readiness');
  const [id,timer]=pending;timers.delete(id);timer.fn();
  for(let i=0;i<20;i++)await Promise.resolve();
 }
 if(phase!=='success'){
  assert.equal(settled,true,'Unavailable worker must stop pending preparation');
  assert.equal(ctx.offlineShellReady,false);
  assert.equal(messages.at(-1)?.kind,'warn');
 }else{
  assert.equal(settled,true);
  assert.equal(ctx.offlineShellReady,true);
  assert.equal(messages.at(-1)?.kind,'ok');
 }
 assert.equal(timers.size,0,'Startup/status deadlines must be released');
 assert(ports.length===0||ports[0].closed,'Always close the owned response port');
 if(phase==='postMessageThrow')assert(ports[1].closed,'Close an untransferred outgoing port');
 await task;
}
run().catch(e=>{console.error(e);process.exit(1);});
'''.replace('PHASE', json.dumps(phase)))

    def test_offline_preparation_bounds_unresolved_worker_registration(self):
        self.run_offline_preparation('register')

    def test_offline_preparation_bounds_unresolved_worker_readiness(self):
        self.run_offline_preparation('ready')

    def test_offline_preparation_releases_deadlines_after_success(self):
        self.run_offline_preparation('success')

    def test_offline_preparation_cleans_up_when_status_post_throws(self):
        self.run_offline_preparation('postMessageThrow')

    def test_offline_preparation_closes_reply_port_after_status_timeout(self):
        self.run_offline_preparation('statusTimeout')

    def emitted_fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        repo = Path(temp.name)
        dash = repo / 'dashboard'
        (dash / 'assets').mkdir(parents=True)
        for name in ('sw.js', 'manifest.webmanifest', '_headers', 'intake.html',
                     'intake-core.js', 'field.html', 'field-core.js', 'field-app.js',
                     'field-quick.js', 'field-sync.js', 'field.webmanifest', 'assets/logo.png'):
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
        for name in ('field-core.js', 'field-app.js', 'field-quick.js', 'field-sync.js',
                     'intake-core.js', 'field.html',
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
  return new FakeResponse(['/','/field','/intake'].includes(path)?fs.readFileSync('dashboard'+({'/':'/index.html','/field':'/field.html','/intake':'/intake.html'}[path]),'utf8'):'NEW '+path,{url:req.url||req,headers:{'content-type':path.endsWith('.js')?'application/javascript':path.endsWith('.html')||['/','/field','/intake'].includes(path)?'text/html':'image/png'}});
 }};
 vm.runInNewContext(nextScript,nextContext,{filename:'next-built-sw.js'});
 let failedUpgrade;registered.install({waitUntil(p){failedUpgrade=p;}});
 await assert.rejects(failedUpgrade,/synthetic upgrade failure/);
 for(const name of oldBuckets)assert(buckets.has(name),'Active shell was deleted');
 Object.assign(registered,oldListeners);offline=true;
 assert.equal((await respond('field-core.js')).textBody,'ASSET /field-core.js');
 assert.equal((await respond('field-app.js')).textBody,'ASSET /field-app.js');
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
