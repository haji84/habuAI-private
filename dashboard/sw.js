/* HUB NATURAL offline-first field recorder.
 * One authenticated ONLINE install is necessary. This cache contains only
 * application shell assets, never GPS, logs, tokens, or owner raw records.
 * Offline field pages cannot post data or bypass server authorization.
 */
'use strict';
const CACHE = 'hub-natural-static-v6-field-offline';
const SHELL = [
  './','./index.html','./field.html','./field-core.js','./field-app.js',
  './intake.html','./intake-core.js','./manifest.webmanifest',
  './assets/logo.png','./assets/icon-192.png','./assets/icon-512.png',
  './assets/apple-touch-icon.png'
];
const CRITICAL = ['./field.html','./field-core.js','./field-app.js','./intake-core.js'];
const BASE = self.registration.scope;
const absolute = path => new URL(path, BASE).href;
const pathOf = request => new URL(request.url).pathname;
const APP_SHELL = new Set(SHELL.map(path => new URL(path,BASE).pathname));
const FIELD_SHELL = new Set([
  './field.html','./field-core.js','./field-app.js',
  './intake.html','./intake-core.js'
].map(path => new URL(path,BASE).pathname));
const SUMMARY_PATH = new URL('./data/capture_summary.json',BASE).pathname;

function trustedResponse(response,path) {
  if(!response || !response.ok || response.redirected ||
     response.type==='opaque' || response.type==='opaqueredirect') return false;
  const ct = response.headers.get('content-type') || '';
  if(path.endsWith('.html') || path==='./') return ct.toLowerCase().includes('text/html');
  if(path.endsWith('.js')) return /javascript|ecmascript/i.test(ct);
  return true;
}
self.addEventListener('install',event=>{
  event.waitUntil((async()=>{
    const cache=await caches.open(CACHE);
    try {
      for(const path of SHELL){
        const request=new Request(absolute(path),{credentials:'same-origin',cache:'reload'});
        const response=await fetch(request);
        if(!trustedResponse(response,path))throw Error('Offline shell requires authenticated successful asset: '+path);
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
      const cached=await caches.match(absolute('./'+path.split('/').pop()),{cacheName:CACHE});
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
        if(trustedResponse(response,path.endsWith('/')?'./':'./index.html')){
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