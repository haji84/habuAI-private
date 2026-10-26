"""Safety regression for mixed-date local intake and branch-side review package."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_capture_dashboard import CaptureDataError, build
from scripts.import_owner_batch import validate_batch, plan

ROOT = Path(__file__).resolve().parents[1]


class LogIntakeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node needed for JavaScript intake parser")
    def test_browser_parser_groups_by_operational_night_and_never_counts_sightings(self):
        js = r"""
const assert=require('node:assert/strict');
const m=require('./dashboard/intake-core.js');
const log=['ハブログ',
'2026/10/23 0:40','捕獲','ハブ','',
'2026/10/22 20:10','捕獲','ハブ','',
'2026/10/23 0:40','捕獲','ハブ','',
'2026/10/23 21:00','目撃','2匹','クロウサギ','',
'2026/10/25 19:00','エリア探索開始'].join(String.fromCharCode(10));
const p=m.parse(log);
assert.equal(p.blocks,5);
assert.equal(p.exactRepeats,1);
assert.deepEqual(p.nights.map(x=>x.night),['2026-10-22','2026-10-23','2026-10-25']);
assert.equal(p.nights[0].captureHints,2);
assert.equal(p.nights[1].captureHints,0);
assert.equal(p.nights[1].sightings,1);
assert.equal(p.nights[2].starts,1);
assert.equal(m.nightOf(2026,8,2,0,27),'2026-08-01');
assert.equal(m.nightOf(2026,8,2,7,0),'2026-08-02');
assert.equal(m.nightOf(2026,2,30,12,1),null);
const known={asof:'2026-10-24',nights:[{night:'2026-10-22',count:2,effort_confirmed:true}]};
const compare=m.compare(p.nights,known);
assert.equal(compare[0].classification,'登録済み・要照合');
assert.equal(compare[1].classification,'過去日の未登録候補・要審査');
assert.equal(compare[2].classification,'新規候補');
compare[2].approved=true;compare[2].searchConfirmed=true;compare[2].confirmedCount=0;
const batch=m.makeBatch(compare,'2026-10-24',['a'.repeat(64)]);
assert.equal(batch.files.length,1);
assert.equal(batch.files[0].content.capture_count,0);
assert.equal(batch.files[0].path,'data/raw/habu_owner_nights/2026/2026-10-25.json');
assert.throws(()=>m.makeBatch([{...compare[0],approved:true,searchConfirmed:true,confirmedCount:5}],'2026-10-24',[]));
console.log('MIXED_NIGHT_LOCAL_INTAKE_PASS');
"""
        r = subprocess.run(["node", "-e", js], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_html_ships_without_public_write_endpoint(self):
        html = (ROOT / "dashboard/intake.html").read_text(encoding="utf-8")
        core = (ROOT / "dashboard/intake-core.js").read_text(encoding="utf-8")
        builder = (ROOT / "scripts/build_capture_dashboard.py").read_text(encoding="utf-8")
        self.assertIn("intake-core.js", html)
        self.assertIn("crypto.subtle.digest('SHA-256'", html)
        self.assertIn("登録はまだ行っていません", html)
        self.assertIn("既存集計を取得できません", html)
        self.assertIn('("sw.js", "manifest.webmanifest", "_headers", "intake.html", "intake-core.js")', builder)
        self.assertNotIn("GITHUB_TOKEN", html + core)
        self.assertNotIn("api.github.com", html + core)
        self.assertIn('href="./intake.html"', (ROOT / "dashboard/index.html").read_text(encoding="utf-8"))

    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        target = Path(temp.name)
        d = target / "dashboard"
        d.mkdir()
        for name in ("baseline_2026.json", "owner_effort_2026-10-26.json"):
            (d / name).write_bytes((ROOT / "dashboard" / name).read_bytes())
        return target

    @staticmethod
    def batch(night="2026-10-27", count=2):
        return {
            "schema_version": "habu-local-intake-review-batch-v1",
            "baseline_asof": "2026-10-24", "source_sha256": ["a" * 64],
            "requires_server_reconciliation": True,
            "counts_are_owner_confirmed_not_scientific_labels": True,
            "files": [{
                "path": f"data/raw/habu_owner_nights/2026/{night}.json",
                "content": {
                    "schema_version": "habu-owner-night-v1",
                    "source": "user Habu log", "operational_date": night,
                    "owner_confirmed": True, "search_performed": True,
                    "capture_count": count, "revision": 1
                },
            }],
        }

    def test_batch_plans_without_touching_original_and_reapply_is_idempotent(self):
        repo = self.make_repo()
        before = build(repo)
        payload = self.batch()
        towrite, skip = plan(repo, payload)
        self.assertEqual((len(towrite), len(skip)), (1, 0))
        self.assertEqual(build(repo)["total"], before["total"])
        for path, record in towrite:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(build(repo)["total"], 251)
        towrite2, skip2 = plan(repo, payload)
        self.assertEqual((len(towrite2), len(skip2)), (0, 1))

    def test_conflicting_or_historic_nights_refused(self):
        repo = self.make_repo()
        with self.assertRaises(CaptureDataError):
            plan(repo, self.batch("2026-10-24", 4))
        bad = self.batch()
        bad["files"][0]["content"]["latitude"] = 28.1
        with self.assertRaises(CaptureDataError):
            validate_batch(bad)
        bad = self.batch()
        bad["files"][0]["path"] = "../bad.json"
        with self.assertRaises(CaptureDataError):
            validate_batch(bad)
        bad = self.batch()
        bad["source_sha256"] = ["not-a-sha"]
        with self.assertRaises(CaptureDataError):
            validate_batch(bad)
        file = repo / "data/raw/habu_owner_nights/2026/2026-10-27.json"
        file.parent.mkdir(parents=True)
        file.write_text('{"capture_count":9}', encoding="utf-8")
        with self.assertRaises(CaptureDataError):
            plan(repo, self.batch())


if __name__ == "__main__":
    unittest.main()
