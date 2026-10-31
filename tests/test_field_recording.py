"""Mobile field recorder: source-only GPS, honest gaps, owner counts, and page wiring."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FieldRecordingTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_overnight_gps_gpx_and_non_capture_events(self):
        code = r"""
const assert=require('node:assert/strict');
const c=require('./dashboard/field-core.js');
const s=c.createSession('mobile-session-aaaaaaaa-001','2026-10-27T12:00:00.000Z');
assert.equal(c.night('2026-10-27T21:59:00Z'),'2026-10-27');
assert.equal(c.night('2026-10-27T22:00:00Z'),'2026-10-28');
assert.equal(c.clockJst(s.startedAt),'2026/10/27 21:00:00');
const a={latitude:28.01,longitude:129.21,accuracy:7,altitude:22};
assert.equal(c.recordPoint(s,a,'2026-10-27T12:01:00Z'),true);
assert.equal(c.recordPoint(s,a,'2026-10-27T12:01:00Z'),false);
c.markGap(s,'2026-10-27T12:02:00Z','画面ロック');
c.recordPoint(s,{...a,latitude:28.02},'2026-10-27T12:08:00Z');
c.event(s,{id:'observed-entry-00000001',time:'2026-10-27T12:12:00Z',type:'capture',species:'ハブ',count:2,owner:'self',note:'大きな個体'});
c.event(s,{id:'observed-entry-00000002',time:'2026-10-27T12:13:00Z',type:'sighting',species:'ハブ',count:3,owner:'self'});
c.event(s,{id:'observed-entry-00000003',time:'2026-10-27T12:14:00Z',type:'capture',species:'ヒメハブ',count:1,owner:'self'});
c.event(s,{id:'observed-entry-00000004',time:'2026-10-27T12:15:00Z',type:'capture',species:'ハブ',count:4,owner:'other'});
assert.equal(c.canUse('FREE','gpsRecord'),true);
assert.equal(c.canUse('FREE','gpsExport'),false);
assert.equal(c.canUse('TRACK','gpsExport'),true);
assert.equal(c.canUse('AI','aiPrediction'),true);
assert.equal(c.canUse('AI','routeOptimization'),false);
assert.equal(c.canUse('PREMIUM','routeOptimization'),true);
assert.equal(c.canUse('INVALID','gpsRecord'),false);
assert.equal(c.canUse('PREMIUM','unknown'),false);
assert.equal(c.summary(s)[0].ownerHabuCaptures,2);
const xml=c.gpx(s);
assert.equal((xml.match(/<trkseg>/g)||[]).length,2);
assert.equal((xml.match(/<trkpt /g)||[]).length,2);
assert(!xml.includes('12:02:00Z</time>'));
const log=c.logfile(s);
assert(log.includes('捕獲'));
assert(log.includes('クロウサギ')===false);
c.stop(s,'2026-10-27T13:00:00Z');
assert(s.endedAt);
assert.throws(()=>c.event(s,{id:'forbidden-00000000000001',time:'2026-10-27T13:01:00Z',type:'capture',species:'ハブ',count:1}));
assert.equal(c.summary(s)[0].ownerHabuCaptures,2);
assert.equal(JSON.parse(c.exportBackup(s)).points.length,2);
assert.throws(()=>c.observedPoint({latitude:1000,longitude:20,accuracy:5},Date.now()));
console.log('FIELD_RECORDING_OK');
"""
        r = subprocess.run(["node", "-e", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_ui_javascript_syntax(self):
        for name in ("field-core.js", "field-app.js", "intake-core.js"):
            source = ROOT / "dashboard" / name
            r = subprocess.run(["node", "--check", str(source)],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, name + " " + r.stderr)

    def test_build_includes_source_only_protected_field_app(self):
        html = (ROOT / "dashboard/field.html").read_text(encoding="utf-8")
        script = (ROOT / "dashboard/field-app.js").read_text(encoding="utf-8")
        core = (ROOT / "dashboard/field-core.js").read_text(encoding="utf-8")
        builder = (ROOT / "scripts/build_capture_dashboard.py").read_text(encoding="utf-8")
        sw = (ROOT / "dashboard/sw.js").read_text(encoding="utf-8")
        self.assertIn("watchPosition", script)
        self.assertIn("indexedDB", script)
        self.assertIn("persist()", script)
        self.assertIn("const active=existing.filter", script)
        self.assertIn("session=core.validateSession(active[0])", script)
        self.assertIn("GPSは自動再開しません", script)
        self.assertIn("GPS再開", script)
        self.assertIn("GPXを保存", html)
        self.assertIn("記録一式バックアップ", html)
        self.assertIn("GPS実測点", core) if "GPS実測点" in core else self.assertIn("accuracyMeters", core)
        self.assertIn('"field.html"', builder)
        self.assertIn("'./field-app.js'", sw)
        self.assertIn('href="./field.html"', (ROOT / "dashboard/index.html").read_text(encoding="utf-8"))
        self.assertNotIn("api.github.com", script + html)
        self.assertNotIn("GITHUB_TOKEN", script + html)
        self.assertNotIn("fetch('/api/", script + html)


if __name__ == "__main__":
    unittest.main()
