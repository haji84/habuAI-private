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
for(const button of buttons)button.addEventListener('click',()=>record(button));
window.HabuFieldQuick={
 ack(ok,message){
   if(!lastTap)return;
   lastTap=0;
   say(ok?'端末に保存済み: '+message:'端末への保存失敗: '+message,ok?'ok':'bad');
 }
};
})();
