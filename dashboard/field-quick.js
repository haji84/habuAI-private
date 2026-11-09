/* One-touch FIELD controls. Reuse the verified field-app event/save path.
 * No GPS writes, external network calls, or scientific labels are added here. */
(function(){
'use strict';
const $=id=>document.getElementById(id);
const buttons=Array.from(document.querySelectorAll('[data-quick-type]'));
const status=$('quickStatus');
let lastKey='',lastTap=0;
function say(message,kind='normal'){
 if(!status)return;
 status.textContent=message;status.dataset.kind=kind;
}
function record(button){
 const add=$('add');
 if(!add||add.disabled){
   say('先に「探索を開始」してください。保存エラーがある場合はバックアップを優先。','warn');
   return;
 }
 const type=button.dataset.quickType,species=button.dataset.quickSpecies,
       owner=button.dataset.quickOwner||'self';
 if(!['capture','sighting','roadkill','other'].includes(type)||
    !species||!['self','other'].includes(owner))return;
 const key=type+'|'+species+'|'+owner,now=Date.now();
 if(key===lastKey && now-lastTap<450){
   say('連続タップを検出。直前の記録結果を確認してください。','warn');return;
 }
 lastKey=key;lastTap=now;
 const names=['type','species','speciesOther','owner','count','note','observedAt','timeUncertainty'];
 const old={};for(const name of names)old[name]={value:$(name)?.value,hidden:$(name)?.hidden};
 const speciesBox=$('species'),extra=$('speciesOther');
 try {
   $('type').value=type;
   const known=speciesBox.options&&Array.from(speciesBox.options).some(o=>o.value===species);
   speciesBox.value=known?species:'other';
   if(!known&&extra){extra.value=species;extra.hidden=false;}
   $('owner').value=owner;$('count').value='1';$('note').value='';
   $('observedAt').value='';$('timeUncertainty').value='';
   // click() invokes the existing field-app handler synchronously through
   // core.event(), then that controller commits via its serialized IndexedDB queue.
   add.click();
   say(species+'（'+(type==='capture'?'捕獲':type==='sighting'?'目撃':type==='roadkill'?'轢死':'その他')+'）の保存処理中。','warn');
 }catch(e){say('記録を開始できません: '+String(e.message),'bad');}
 finally {
   for(const name of names){
     const el=$(name);
     if(el){el.value=old[name].value;el.hidden=old[name].hidden;}
   }
 }
}
// Keep the wildlife grid compact: a mode switch changes classification,
// not species, while the same verified IndexedDB save path remains in use.
const faunaButtons=buttons.filter(b=>b.dataset.quickFauna==='true');
const sight=$('faunaModeSighting'),road=$('faunaModeRoadkill');
function faunaMode(type){
 if(type!=='sighting'&&type!=='roadkill')return;
 for(const b of faunaButtons){
  b.dataset.quickType=type;
  b.classList.remove('sighting','roadkill');
  b.classList.add(type);
  b.setAttribute('aria-label',b.dataset.quickSpecies+'を'+(type==='roadkill'?'轢死':'目撃')+'として1匹記録');
 }
 if(sight)sight.setAttribute('aria-pressed',String(type==='sighting'));
 if(road)road.setAttribute('aria-pressed',String(type==='roadkill'));
 say('ほかの生き物：'+(type==='roadkill'?'轢死':'目撃')+'モード。生き物のボタンで保存。','normal');
}
if(sight&&road){
 sight.addEventListener('click',()=>faunaMode('sighting'));
 road.addEventListener('click',()=>faunaMode('roadkill'));
}
for(const button of buttons)button.addEventListener('click',()=>record(button));
window.HabuFieldQuick={
 ack(ok,message){
   if(!lastTap)return;
   lastTap=0;
   say(ok?'端末に保存済み: '+message:'端末への保存失敗: '+message,ok?'ok':'bad');
 }
};
})();
