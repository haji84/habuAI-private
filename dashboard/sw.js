/* HUB NATURAL offline-first field recorder.
 * One authenticated ONLINE install is necessary. This cache contains only
 * application shell assets, never GPS, logs, tokens, or owner raw records.
 * Offline field pages cannot post data or bypass server authorization.
 */
'use strict';
// The dashboard builder adds a content digest of this worker and its shell.
const CACHE = 'hub-natural-static-v8-field-restore';
const SHELL = [
  './','./index.html','./field.html','./field-core.js','./field-app.js','./field-crypto.js','./field-quick.js','./field-sync.js',
  './intake.html','./intake-core.js','./manifest.webmanifest','./field.webmanifest',
  './assets/logo.png','./assets/icon-192.png','./assets/icon-512.png',
  './assets/apple-touch-icon.png'
];
const CRITICAL = ['./field.html','./field-core.js','./field-app.js','./field-crypto.js','./field-quick.js','./field-sync.js','./intake.html','./intake-core.js'];
const BASE = self.registration.scope;
const absolute = path => new URL(path, BASE).href;
const pathOf = request => new URL(request.url).pathname;
// Keep physical asset names for the builder/cache, but fetch Pages' canonical
// HTML URLs so a legitimate .html redirect never weakens login rejection.
const HTML_FETCH_PATHS = new Map([
  ['./index.html','./'],['./field.html','./field'],['./intake.html','./intake']
]);
const APP_SHELL = new Set(SHELL.map(path => new URL(path,BASE).pathname));
const FIELD_SHELL = new Map([
  './field.html','./field-core.js','./field-app.js','./field-crypto.js','./field-quick.js','./field-sync.js',
  './intake.html','./intake-core.js'
].map(path => [new URL(path,BASE).pathname,path]));
for(const [asset,path] of HTML_FETCH_PATHS){
  if(FIELD_SHELL.has(new URL(asset,BASE).pathname)){
    FIELD_SHELL.set(new URL(path,BASE).pathname,asset);
  }
}
const SUMMARY_PATH = new URL('./data/capture_summary.json',BASE).pathname;

function responseAt(response,url) {
  return !!response && !response.redirected && response.type!=='opaque' &&
    response.type!=='opaqueredirect' && response.type!=='cors' && response.url===url &&
    new URL(url).origin===new URL(BASE).origin;
}
function trustedResponse(response,path,url) {
  if(!response || !response.ok || response.redirected ||
     !responseAt(response,url)) return false;
  const ct = response.headers.get('content-type') || '';
  if(path.endsWith('.html') || path==='./') return ct.toLowerCase().includes('text/html');
  if(path.endsWith('.js')) return /javascript|ecmascript/i.test(ct);
  return true;
}
async function htmlRoleMatches(response,path) {
  if(!HTML_FETCH_PATHS.has(path) && path!=='./')return true;
  // Fixed page markers check content role, not authentication or full integrity.
  const markers=path==='./field.html'?['id="offlineState"','src="./field-core.js"','src="./field-app.js"']:
    path==='./intake.html'?['id="files"','id="analyze"','src="./intake-core.js"']:['id="snapshot"'];
  const reader=response.clone().body?.getReader();
  if(!reader)return false;
  const decoder=new TextDecoder();let bytes=0,text='',matched=false;
  try{
    while(true){
      const part=await reader.read();if(part.done)break;
      bytes+=part.value.byteLength;if(bytes>2*1024*1024)return false;
      text+=decoder.decode(part.value,{stream:true});
    }
    text+=decoder.decode();matched=markers.every(marker=>text.includes(marker));return matched;
  }finally{
    // A cloned body is a tee: waiting for just one cancelled branch can wait
    // forever while the other branch is unread. Reject without that wait.
    reader.cancel().catch(()=>{});reader.releaseLock();
    if(!matched)response.body?.cancel().catch(()=>{});
  }
}
async function shellResponse(path) {
  const networkPath=HTML_FETCH_PATHS.get(path)||path;
  let url=absolute(networkPath);
  const request=target=>new Request(target,{credentials:'same-origin',cache:'reload',redirect:'error'});
  let response=await fetch(request(url));
  // A missing canonical route may use only its fixed physical HTML counterpart.
  if(networkPath!==path && responseAt(response,url) && response.status===404){
    url=absolute(path);response=await fetch(request(url));
  }
  if(!trustedResponse(response,path,url) || !await htmlRoleMatches(response,path))
    throw Error('Offline shell requires authenticated successful asset: '+path);
  return response;
}
self.addEventListener('install',event=>{
  event.waitUntil((async()=>{
    const cache=await caches.open(CACHE);
    try {
      for(const path of SHELL){
        const request=new Request(absolute(path),{credentials:'same-origin',cache:'reload'});
        const response=await shellResponse(path);
        await cache.put(request,response);
      }
      await self.skipWaiting();
    } catch(error) {
      await caches.delete(CACHE);
      throw error;
    }
  })());
});
self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{
    // Never wipe another application's caches.
    const keys=await caches.keys();
    await Promise.all(keys.filter(k=>k.startsWith('hub-natural-static-') && k!==CACHE).map(k=>caches.delete(k)));
    await self.clients.claim();
  })());
});
self.addEventListener('message',event=>{
  if(!event.data || event.data.type!=='HABU_FIELD_OFFLINE_STATUS')return;
  event.waitUntil((async()=>{
    try {
      const cache=await caches.open(CACHE);
      const flags=await Promise.all(CRITICAL.map(path=>cache.match(absolute(path)).then(Boolean)));
      if(event.ports && event.ports[0])event.ports[0].postMessage({
        type:'HABU_FIELD_OFFLINE_STATUS',ready:flags.every(Boolean),version:CACHE
      });
    } catch(error) {
      if(event.ports && event.ports[0])event.ports[0].postMessage({
        type:'HABU_FIELD_OFFLINE_STATUS',ready:false
      });
    }
  })());
});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  if(url.origin!==new URL(BASE).origin)return;
  const path=url.pathname;
  if(FIELD_SHELL.has(path)){
    event.respondWith((async()=>{
      const cached=await caches.match(absolute(FIELD_SHELL.get(path)),{cacheName:CACHE});
      if(cached)return cached;
      // Never cache an Access sign-in page as the offline recorder.
      return fetch(event.request);
    })());
    return;
  }
  if(path===SUMMARY_PATH){
    const mustBeFresh=url.searchParams.get('require_fresh')==='1';
    const stable=absolute('./data/capture_summary.json');
    event.respondWith((async()=>{
      try {
        const response=await fetch(event.request);
        if(response.ok&&!response.redirected&&
           (response.headers.get('content-type')||'').toLowerCase().includes('json')){
          const cache=await caches.open(CACHE);
          event.waitUntil(cache.put(stable,response.clone()));
        }
        if(mustBeFresh && (!response.ok || response.redirected ||
           !(response.headers.get('content-type')||'').toLowerCase().includes('json')))
          return Response.error();
        return response;
      }catch(error){return mustBeFresh ? Response.error() : (await caches.match(stable) || Response.error());}
    })());
    return;
  }
  if(url.pathname===new URL('./index.html',BASE).pathname ||
     url.pathname===new URL('./',BASE).pathname){
    event.respondWith((async()=>{
      try{
        const response=await fetch(event.request);
        const asset=path.endsWith('/')?'./':'./index.html';
        if(trustedResponse(response,asset,event.request.url) && await htmlRoleMatches(response,asset)){
          const cache=await caches.open(CACHE);
          event.waitUntil(cache.put(event.request,response.clone()));
        }
        return response;
      }catch(error){return await caches.match(event.request) ||
        await caches.match(absolute('./index.html')) || Response.error();}
    })());
    return;
  }
  if(APP_SHELL.has(path)){
    event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request)));
  }
});
