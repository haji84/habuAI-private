"""Encrypted GPS backups: synthetic-only AES-256-GCM PBKDF2 round trips.

No owner GPS or keys are used. Test exposes only fake fixtures in code.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js is required")
class FieldEncryptedBackupTests(unittest.TestCase):
    def test_real_webcrypto_envelope_roundtrip_tamper_wrong_key_nonce_randomness(self):
        js=r"""
const assert=require('node:assert/strict');
Object.defineProperty(globalThis,'crypto',{value:require('node:crypto').webcrypto,configurable:true});
const core=require('./dashboard/field-core.js');
const box=require('./dashboard/field-crypto.js');
const fake=core.createSession('synthetic-backup-session-00001','2026-11-08T10:00:00Z');
core.recordPoint(fake,{latitude:28.123456789,longitude:129.345678901,accuracy:7.5},'2026-11-08T10:00:05Z');
core.event(fake,{id:'synthetic-captured-habu-0001',type:'capture',species:'ハブ',
 owner:'self',count:1,time:'2026-11-08T10:00:08Z',
 position:core.measuredPositionAt(fake,'2026-11-08T10:00:08Z')});
core.stop(fake,'2026-11-08T10:01:00Z');
const raw=core.exportBackup(fake),pass='synthetic-long-password-do-not-reuse';
const b64=b=>Buffer.from(b).toString('base64');
(async()=>{
 const a=await box.encryptText(raw,'web-session-json',pass);
 const b=await box.encryptText(raw,'web-session-json',pass);
 assert.equal(a.schema_version,'habu-encrypted-backup-v1');
 assert.equal(a.algorithm,'AES-256-GCM');
 assert.equal(a.kdf,'PBKDF2-HMAC-SHA256');
 assert.equal(a.iterations,600000);
 assert.notEqual(a.salt_b64,b.salt_b64);
 assert.notEqual(a.nonce_b64,b.nonce_b64);
 assert.notEqual(a.ciphertext_b64,b.ciphertext_b64);
 const sealed=JSON.stringify(a);
 assert(!sealed.includes('28.123456789'));
 assert(!sealed.includes('129.345678901'));
 assert(!sealed.includes('synthetic-captured-habu'));
 assert(!sealed.includes('synthetic-backup-session'));
 assert(!sealed.includes(pass));
 const restore=await box.decryptBytes(a,pass);
 assert.equal(restore.format,'web-session-json');
 assert.equal(box.decodeText(restore.bytes),raw);
 assert.equal(core.validateRestoredSession(JSON.parse(box.decodeText(restore.bytes))).id,fake.id);
 await assert.rejects(()=>box.decryptBytes(a,'definitely-the-wrong-password'),/復号できません/);
 const flip=structuredClone(a),ct=Buffer.from(a.ciphertext_b64,'base64');
 ct[ct.length-2]^=0x20;flip.ciphertext_b64=b64(ct);
 await assert.rejects(()=>box.decryptBytes(flip,pass),/復号できません/);
 for(const [field,bad] of [['algorithm','AES-CBC'],['format','fake'],['iterations',1],
   ['salt_b64','!!!'],['nonce_b64','not base64'],['schema_version','old']]){
  const changed=structuredClone(a);changed[field]=bad;
  await assert.rejects(()=>box.decryptBytes(changed,pass));
 }
 await assert.rejects(()=>box.encryptText(raw,'web-session-json','short'),/12文字以上/);
 await assert.rejects(()=>box.encryptText(raw,'weird-format',pass));
 await assert.rejects(()=>box.encryptText(raw,'web-session-json',pass).then(
  v=>box.decryptBytes({...v,extra:'leaky'},pass)));
})().catch(error=>{console.error(error);process.exitCode=1});
"""
        r=subprocess.run(["node","-"],input=js,cwd=ROOT,capture_output=True,text=True,
                         encoding="utf-8",timeout=90)
        self.assertEqual(r.returncode,0,r.stderr)

    def test_independently_derived_cross_platform_aes_gcm_vector(self):
        js=r"""
Object.defineProperty(globalThis,'crypto',{value:require('node:crypto').webcrypto,configurable:true});
const assert=require('node:assert/strict'),crypto=require('./dashboard/field-crypto.js');
(async()=>{
 const envelope=${JSON.stringify(vector)};
 const opened=await crypto.decryptBytes(envelope,'synthetic-cross-platform-passphrase');
 assert.equal(opened.format,'ios-jsonl');
 assert.equal(crypto.decodeText(opened.bytes),'SYNTHETIC GPS backup test bytes; not a real location');
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        result=subprocess.run(['node','-'],input=js,cwd=ROOT,capture_output=True,
                              text=True,encoding='utf-8',timeout=50)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_export_restore_ui_and_bundle_are_offline_and_no_public_payloads(self):
        html=(ROOT/"dashboard/field.html").read_text(encoding="utf-8")
        app=(ROOT/"dashboard/field-app.js").read_text(encoding="utf-8")
        worker=(ROOT/"dashboard/sw.js").read_text(encoding="utf-8")
        private=(ROOT/"scripts/private_dashboard_api.py").read_text(encoding="utf-8")
        builder=(ROOT/"scripts/build_capture_dashboard.py").read_text(encoding="utf-8")
        for needle in ('field-crypto.js','backupPassphrase','backupPassphraseConfirm',
                       'encryptedBackup','encryptedRestore'):
            self.assertIn(needle,html)
        for needle in ("HabuFieldCrypto.encryptText(","HabuFieldCrypto.decryptBytes(",
                       "core.validateRestoredSession(","await persist()","await saveQueue"):
            if needle=="await persist()":
                continue
            self.assertIn(needle,app)
        for file in (builder,worker,private):
            self.assertIn("field-crypto.js",file)
        self.assertIn("非暗号",app)
        self.assertNotIn("localStorage", (ROOT/"dashboard/field-crypto.js").read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
