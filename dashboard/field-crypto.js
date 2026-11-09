/* HABU FIELD v1 encrypted backup envelope.
 * Authenticated AES-256-GCM with a fresh random 16-byte PBKDF2 salt and
 * 12-byte nonce per export. Do not store passwords, derived keys, or raw logs
 * in Git, caches, service worker data, application logs or network calls.
 * This encrypts BACKUP FILES, not the existing local recording database.
 */
(function(root,factory){
 'use strict';
 const api=factory(root);
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.HabuFieldCrypto=api;
})(typeof window!=='undefined'?window:globalThis,function(root){
 'use strict';
 const VERSION='habu-encrypted-backup-v1';
 const CIPHER='AES-256-GCM',KDF='PBKDF2-HMAC-SHA256',ROUNDS=600000;
 const AAD_PREFIX='HABU-ENCRYPTED-BACKUP-V1|';
 const SALT_BYTES=16,NONCE_BYTES=12,MAX_PLAIN=30*1024*1024;
 const FORMATS=['web-session-json','ios-jsonl'];
 const encoder=new TextEncoder(),decoder=new TextDecoder('utf-8',{fatal:true});
 function secureCrypto(){
  const c=root&&root.crypto;
  if(!c||!c.subtle||typeof c.getRandomValues!=='function')
   throw Error('安全なHTTPS環境の暗号機能が必要です');
  return c;
 }
 function base64(bytes){
  let out='';
  for(let i=0;i<bytes.length;i+=8192)
   out+=String.fromCharCode(...bytes.subarray(i,i+8192));
  return btoa(out);
 }
 function fromBase64(text,size){
  if(typeof text!=='string'||text.length>size*2+8||
    !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(text))
   throw Error('暗号ファイルの文字形式が不正');
  const binary=atob(text),out=Uint8Array.from(binary,c=>c.charCodeAt(0));
  if(out.length>size)throw Error('暗号ファイルが大きすぎます');
  return out;
 }
 function passwordCheck(pass){
  if(typeof pass!=='string'||Array.from(pass).length<12||pass.length>1024)
   throw Error('12文字以上の復元用パスフレーズが必要です');
  return encoder.encode(pass);
 }
 async function keyFor(pass,salt){
  const c=secureCrypto();
  const material=await c.subtle.importKey('raw',passwordCheck(pass),{name:'PBKDF2'},false,['deriveKey']);
  return c.subtle.deriveKey({name:'PBKDF2',salt,iterations:ROUNDS,hash:'SHA-256'},
    material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
 }
 function aad(format){return encoder.encode(AAD_PREFIX+format);}
 function randomBytes(n){const value=new Uint8Array(n);secureCrypto().getRandomValues(value);return value;}
 async function encryptBytes(bytes,format,pass){
  if(!FORMATS.includes(format))throw Error('バックアップの内容形式が未対応');
  if(!(bytes instanceof Uint8Array)||bytes.length<1||bytes.length>MAX_PLAIN)
   throw Error('バックアップは1バイト以上、30MiB以下にしてください');
  const salt=randomBytes(SALT_BYTES),nonce=randomBytes(NONCE_BYTES);
  const key=await keyFor(pass,salt);
  const sealed=new Uint8Array(await secureCrypto().subtle.encrypt(
    {name:'AES-GCM',iv:nonce,additionalData:aad(format),tagLength:128},key,bytes));
  return {schema_version:VERSION,algorithm:CIPHER,kdf:KDF,iterations:ROUNDS,
          format,salt_b64:base64(salt),nonce_b64:base64(nonce),
          ciphertext_b64:base64(sealed)};
 }
 async function decryptBytes(envelope,pass){
  if(!envelope||typeof envelope!=='object'||Array.isArray(envelope)||
    Object.keys(envelope).sort().join(',')!==
      ['schema_version','algorithm','kdf','iterations','format',
       'salt_b64','nonce_b64','ciphertext_b64'].sort().join(',')||
    envelope.schema_version!==VERSION||envelope.algorithm!==CIPHER||
    envelope.kdf!==KDF||envelope.iterations!==ROUNDS||
    !FORMATS.includes(envelope.format))
   throw Error('暗号ファイルの形式が不正');
  const salt=fromBase64(envelope.salt_b64,SALT_BYTES),
        nonce=fromBase64(envelope.nonce_b64,NONCE_BYTES),
        cipher=fromBase64(envelope.ciphertext_b64,MAX_PLAIN+16);
  if(salt.length!==SALT_BYTES||nonce.length!==NONCE_BYTES||cipher.length<17)
   throw Error('暗号ファイルの長さが不正');
  const key=await keyFor(pass,salt);
  let plain;
  try{
   plain=new Uint8Array(await secureCrypto().subtle.decrypt(
     {name:'AES-GCM',iv:nonce,additionalData:aad(envelope.format),tagLength:128},
     key,cipher));
  }catch(_){throw Error('復号できません。パスフレーズ違い、またはファイルの破損です');}
  if(plain.length>MAX_PLAIN)throw Error('復号後のサイズ上限を超えています');
  return {format:envelope.format,bytes:plain};
 }
 async function encryptText(text,format,pass){
  if(typeof text!=='string')throw Error('暗号化する原本が不正');
  return encryptBytes(encoder.encode(text),format,pass);
 }
 function decodeText(bytes){return decoder.decode(bytes);}
 return Object.freeze({VERSION,ROUNDS,MAX_PLAIN,encryptBytes,decryptBytes,encryptText,decodeText});
});
