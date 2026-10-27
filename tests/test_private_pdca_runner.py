import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from private_pdca_runner import run_private, PrivateRunError


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.code, self.store, self.workspace = (base / v for v in ("code", "store", "work"))
        for p in (self.code, self.store, self.workspace):
            p.mkdir(mode=0o700)
        (self.code / "scripts").mkdir()
        (self.code / "scripts" / "run_pdca.py").write_text(
            'import json\nprint(json.dumps({"overall_status":"BLOCKED"}))\nraise SystemExit(2)\n')
        raw = self.store / "raw" / "log"
        raw.mkdir(parents=True)
        self.source = raw / "source.txt"
        self.source.write_text("2026/10/26 19:55\n捕獲\nハブ捕獲~90幼体\n")
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.rec = self.store / "receipt.json"
        self.rec.write_text(json.dumps({"receipt_id": "a"*64, "sources": [{
            "type": "log", "sha256": digest, "size_bytes": self.source.stat().st_size,
            "private_archive": str(self.source)}]}))

    def test_repeated_run_same_sources_no_double_count(self):
        x = run_private(self.code, self.workspace, self.store, self.rec, "2026-10-26")
        y = run_private(self.code, self.workspace, self.store, self.rec, "2026-10-26")
        self.assertEqual(x, y)
        self.assertEqual(x["overall_status"], "BLOCKED")
        self.assertEqual(len(list((self.store/"private_pdca_runs").glob("*.json"))), 1)

    def test_modified_original_rejected(self):
        self.source.write_text("tampered")
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2026-10-26")

    def test_private_path_cannot_be_public_repo(self):
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.code, self.store, self.rec, "2026-10-26")

    def test_bad_night_rejected(self):
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2026-10-26;rm")

    def test_symlink_to_external_raw_rejected(self):
        outside = self.workspace / "outside.txt"
        outside.write_bytes(self.source.read_bytes())
        self.source.unlink()
        self.source.symlink_to(outside)
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2026-10-26")

    def test_engine_success_does_not_grant_scientific_certification(self):
        (self.code / "scripts" / "run_pdca.py").write_text(
            'import json\nprint(json.dumps({"overall_status":"PASS"}))\n')
        result = run_private(self.code, self.workspace, self.store, self.rec, "2026-10-26")
        self.assertEqual(result["model_validation"], "NOT_CERTIFIED")
        self.assertEqual(result["p0"], "NOT_CERTIFIED")


if __name__ == "__main__":
    unittest.main()
