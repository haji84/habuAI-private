"""Privacy-preserving durable encryption tests. All rows are synthetic.

No actual user GPS, decryption key, token or encrypted artifact is committed.
The private production API is not allowed to boot without its own 256-bit key.
"""
from __future__ import annotations
import base64
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class PrivateDurableEncryptionTests(unittest.TestCase):
    def setUp(self):
        from scripts.private_dashboard_store import Store
        from scripts.private_dashboard_crypto import SourceCipher, MAGIC
        self.Store=Store;self.SourceCipher=SourceCipher;self.MAGIC=MAGIC
        self.tmp=tempfile.TemporaryDirectory(prefix="habu-encrypted-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.seed=self.home/"seed";(self.seed/"dashboard").mkdir(parents=True)
        baseline={"as_of_operational_night":"2026-10-30",
            "months":[{"key":"2026-10","n":1}],
            "nights":[{"night":"2026-10-30","month":"2026-10","count":1,
                "start":"不明","end":"不明","events":None}],
            "notes":["SYNTHETIC ENCRYPTED TEST ONLY"]}
        (self.seed/"dashboard/baseline_2026.json").write_text(
            json.dumps(baseline),encoding="utf-8")
        self.key=b"k"*32  # synthetic key, never reuse for actual user data
        self.assertEqual(len(self.key),32)
        self.store=Store(self.home/"private",self.seed,code_root=ROOT,
                         encryption_key=self.key)

    def test_private_source_blobs_seed_and_GPX_are_ciphertext_not_plaintext(self):
        from test_private_dashboard_sync import LOG,GPX,upload,batch
        prepared=self.store.prepare([upload("log",LOG.encode()),upload("gpx",GPX)],channel="dashboard")
        self.assertEqual(prepared["state"],"READY_FOR_CONFIRMATION")
        with closing(sqlite3.connect(self.store.db_path)) as db:
            seed=db.execute("SELECT sha,body FROM seed").fetchone()
            blobs=db.execute("SELECT sha,kind,body FROM blobs ORDER BY kind").fetchall()
        self.assertTrue(seed[1].startswith(self.MAGIC))
        self.assertNotIn(b"2026-10-30",seed[1])
        self.assertEqual(len(blobs),2)
        self.assertTrue(all(b.startswith(self.MAGIC) for _,_,b in blobs))
        self.assertFalse(any(b"trkpt" in body for _,_,body in blobs))
        self.assertFalse(any("エリア探索開始".encode() in body for _,_,body in blobs))
        from scripts.private_dashboard_inputs import digest
        for sha,kind,body in blobs:
            clear=self.SourceCipher(self.key).open(body,sha)
            self.assertEqual(digest(clear),sha)
            self.assertIn(kind,{"log","gpx"})
        result=self.store.apply(prepared["receipt_id"],batch(prepared),prepared["revision"])
        self.assertEqual(result["state"],"APPLIED")
        second=self.Store(self.home/"private",self.seed,code_root=ROOT,
                          encryption_key=self.key)
        self.assertEqual(second.snapshot()["revision"],1)
        self.assertEqual(second.snapshot()["summary"]["total"],2)
        self.assertEqual(second.prepare([upload("log",LOG.encode()),upload("gpx",GPX)],
                    channel="chat")["state"],"APPLIED")
        with self.assertRaisesRegex(ValueError,"PRIVATE_SOURCE_ENCRYPTION_REQUIRED"):
            self.Store(self.home/"private",self.seed,code_root=ROOT,
                       encryption_key=b"x"*32)

    def test_ciphertext_changes_each_time_and_tampering_or_wrong_key_is_rejected(self):
        from scripts.private_dashboard_inputs import digest
        from scripts.private_dashboard_crypto import CryptoError
        raw=b"synthetic private GPS original; neither coordinates nor owner identity"
        sha=digest(raw)
        cipher=self.SourceCipher(self.key)
        a=cipher.seal(raw,sha);b=cipher.seal(raw,sha)
        self.assertNotEqual(a,b)
        self.assertNotIn(raw,a)
        self.assertEqual(cipher.open(a,sha),raw)
        broken=bytearray(a);broken[-3]^=4
        with self.assertRaises(CryptoError):cipher.open(bytes(broken),sha)
        with self.assertRaises(CryptoError):cipher.open(a,"0"*64)
        with self.assertRaises(CryptoError):self.SourceCipher(b"y"*32).open(a,sha)
        with self.assertRaises(CryptoError):cipher.open(raw,sha)
        with self.assertRaises(CryptoError):self.SourceCipher(b"weak")

    def test_production_adapter_refuses_start_without_separate_encryption_key(self):
        from scripts.private_dashboard_api import create_app
        from scripts.private_dashboard_crypto import CryptoError,key_from_environment
        environment={"HABU_PRIVATE_ROOT":str(self.home/"production"),
                     "HABU_DASHBOARD_TOKEN":"synthetic-token-only-"+("x"*40),
                     "HABU_DASHBOARD_ORIGIN":"https://private.example"}
        with patch.dict(os.environ,environment,clear=True):
            with self.assertRaises(CryptoError):create_app()
        with patch.dict(os.environ,{**environment,
              "HABU_PRIVATE_ENCRYPTION_KEY_B64":base64.b64encode(b"z"*32).decode()},clear=True):
            self.assertEqual(key_from_environment(),b"z"*32)


if __name__=="__main__":
    unittest.main()
