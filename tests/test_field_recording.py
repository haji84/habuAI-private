"""Mobile field recorder: source-only GPS, honest gaps, owner counts, and page wiring."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FieldRecordingTests(unittest.TestCase):
    def run_js(self, body, *, controller=False):
        if controller:
            from tests.test_field_writer_concurrency import HARNESS
            body = HARNESS + '\n(async()=>{\n' + body + '\n})().catch(e=>{console.error(e);process.exitCode=1;});'
        result = subprocess.run(['node', '-'], input=body, cwd=ROOT,
                                capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_restore_deep_validation_preserves_valid_source_bytes_and_explicit_offsets(self):
        self.run_js(r"""
const assert=require('node:assert/strict'),c=require('./dashboard/field-core.js');
assert.equal(typeof c.validateRestoredSession,'function','missing restore-only validation');
const s=c.createSession('synthetic-restore-aaaaaaaa-001','2026-11-03T19:00:00+09:00');
c.recordPoint(s,{latitude:0,longitude:0,accuracy:5,altitude:-10,speed:0},'2026-11-03T10:00:01Z');
c.event(s,{id:'synthetic-event-aaaaaaaa1',type:'capture',species:'ハブ',count:2,owner:'self',
 time:'2026-11-03T10:00:02Z',note:'SYNTHETIC 原文 unchanged',position:s.points[0]});
c.markGap(s,'2026-11-03T10:00:03Z','SYNTHETIC interruption');c.stop(s,'2026-11-03T10:01:00Z');
s.startedAt='2026-11-03T19:00:00+09:00';s.points[0].time='2026-11-03T19:00:01+09:00';
for(const revision of [undefined,0,5]){
 const source=structuredClone(s);if(revision===undefined)delete source.revision;else source.revision=revision;
 const before=JSON.stringify(source);
 const freeze=x=>{if(x&&typeof x==='object'){Object.values(x).forEach(freeze);Object.freeze(x)}};freeze(source);
 assert.equal(c.validateRestoredSession(source),source);assert.equal(JSON.stringify(source),before);
 assert.equal(JSON.parse(c.exportBackup(source)).events[0].note,s.events[0].note);
}
""")

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_restore_rejects_bad_nested_rows_identity_time_and_counts_without_mutation(self):
        self.run_js(r"""
const assert=require('node:assert/strict'),c=require('./dashboard/field-core.js');
assert.equal(typeof c.validateRestoredSession,'function','missing restore-only validation');
const seed=c.createSession('synthetic-restore-aaaaaaaa-001','2026-11-03T10:00:00Z');
c.recordPoint(seed,{latitude:0,longitude:0,accuracy:5},'2026-11-03T10:00:01Z');
c.event(seed,{id:'synthetic-event-aaaaaaaa1',type:'capture',species:'ハブ',count:1,owner:'self',time:'2026-11-03T10:00:02Z',note:''});
c.markGap(seed,'2026-11-03T10:00:03Z','SYNTHETIC');c.stop(seed,'2026-11-03T10:01:00Z');
const changes=[s=>s.id='bad',s=>s.revision=-1,s=>s.revision=true,s=>s.startedAt='2026-11-03T10:00:00',
 s=>s.startedAt='2026-02-30T10:00:00Z',s=>s.endedAt=null,s=>s.endedAt='2026-11-03T09:59:00Z',
 s=>s.points[0].lat=999,s=>s.points[0].lon=999,s=>s.points[0].accuracy=-1,
 s=>s.points[0].altitude='unmeasured',s=>s.points[0].speed=-1,s=>s.points[0].time='2026-11-03T10:00:01',
 s=>s.points[0].time='2026-11-03T09:59:59Z',s=>s.points.push({...s.points[0],time:'2026-11-03T10:00:00Z'}),
 s=>s.points=Array(200001).fill(s.points[0]),s=>s.events.push({...s.events[0]}),
 s=>s.events[0].count=-5,s=>s.events[0].count=0,s=>s.events[0].count=101,s=>s.events[0].count=1.5,
 s=>s.events[0].owner='unknown',s=>s.events[0].type='made-up',s=>s.events[0].id='bad',
 s=>s.events[0].species={},s=>s.events[0].note={},s=>s.events[0].time='2026-11-03T09:58:59Z',
 s=>s.events[0].position={...s.points[0],lat:999},
 s=>s.events[0].position={...s.points[0],time:'2026-11-03T09:58:00Z'},
 s=>s.gaps[0].time='2026-11-03T10:00:03',s=>s.gaps[0].reason={}];
for(const change of changes){const s=structuredClone(seed);change(s);const before=JSON.stringify(s);
 assert.throws(()=>c.validateRestoredSession(s));assert.equal(JSON.stringify(s),before);}
""")

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_actual_ui_refuses_invalid_restore_before_persisting_any_source_row(self):
        self.run_js(r"""
const seed=fixture();core.stop(seed,'2026-10-27T13:00:00Z');
for(const change of [s=>s.points[0].lat=999,s=>s.events[0].count=-5,
 s=>s.events[0].owner='unknown',s=>s.points[0].time='2026-10-27T12:00:01']){
 const row=copy(seed);change(row);const before=JSON.stringify(row),shared=database([]),tab=await controller(shared);
 const originalText=JSON.stringify(row);await tab.get('restore').handlers.change({target:{value:'synthetic',
  files:[{size:Buffer.byteLength(originalText),text:async()=>originalText}]}});await shared.idle();
 assert.equal(shared.rows.size,0,'invalid source must be rejected before any IDB write');
 assert.equal(JSON.stringify(row),before);assert.match(tab.get('state').textContent,/復元を拒否/);
}
""", controller=True)

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_valid_maximum_point_backup_is_blocked_before_unrestorable_download(self):
        self.run_js(r"""
const seed=core.createSession('synthetic-large-aaaaaaaa-001','2026-11-03T10:00:00Z');
seed.points=Array.from({length:200000},(_,i)=>({time:new Date(Date.parse(seed.startedAt)+i*1000).toISOString(),
 lat:28.123456789012345,lon:129.12345678901234,accuracy:12.3456789012345,
 altitude:123.456789012345,speed:12.3456789012345}));
core.stop(seed,seed.points.at(-1).time);
const bytes=Buffer.byteLength(JSON.stringify(seed,null,2)+'\n');assert(bytes>30*1024*1024);
assert.throws(()=>core.exportBackup(seed),/30/,'must not produce a backup the restore path will reject');
const shared=database([seed]),tab=await controller(shared);await tab.select(seed.id);
let downloads=0;tab.context.document.body.append=()=>{downloads++};
await tab.click('backup');assert.equal(downloads,0);assert.match(tab.get('state').textContent,/30/);
assert.equal(shared.rows.get(seed.id).points.length,200000);
assert.equal(shared.rows.get(seed.id).points.at(-1).time,seed.points.at(-1).time);
""", controller=True)

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_restore_scan_is_not_added_to_live_point_recording(self):
        self.run_js(r"""
const assert=require('node:assert/strict'),c=require('./dashboard/field-core.js');
const s=c.createSession('synthetic-live-aaaaaaaa-001','2026-11-03T10:00:00Z');
const prior={};Object.defineProperty(prior,'lat',{get(){throw Error('deep scan on live GPS fix')}});
s.points=[prior];
assert.doesNotThrow(()=>c.recordPoint(s,{latitude:0,longitude:0,accuracy:5},'2026-11-03T10:00:01Z'));
assert.equal(s.points.length,2);
""")

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_backup_limit_counts_utf8_bytes_and_accepts_the_exact_restore_boundary(self):
        self.run_js(r"""
const assert=require('node:assert/strict'),c=require('./dashboard/field-core.js');
const s=c.createSession('synthetic-utf8-aaaaaaaa-001','2026-11-03T10:00:00Z');
s.events=Array.from({length:40000},(_,i)=>({id:'synthetic-event-'+String(i).padStart(8,'0'),
 type:'capture',species:'ハブ',count:1,owner:'self',time:'2026-11-03T10:00:02.000Z',note:'合'.repeat(300)}));
const text=JSON.stringify(s,null,2)+'\n';
assert(text.length<30*1024*1024);assert(Buffer.byteLength(text,'utf8')>30*1024*1024);
assert.throws(()=>c.exportBackup(s),/30/);assert.equal(s.events.length,40000);
const boundary=c.createSession('synthetic-boundary-aaaaaa-001','2026-11-03T10:00:00Z');boundary.sourceNote='';
const overhead=Buffer.byteLength(JSON.stringify(boundary,null,2)+'\n');
boundary.sourceNote='a'.repeat(30*1024*1024-overhead);
const backup=c.exportBackup(boundary);assert.equal(Buffer.byteLength(backup),30*1024*1024);
assert.equal(c.validateRestoredSession(JSON.parse(backup)).sourceNote.length,boundary.sourceNote.length);
boundary.sourceNote+='a';assert.throws(()=>c.exportBackup(boundary),/30/);
""")

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_actual_ui_valid_restore_preserves_rows_and_backup_roundtrips(self):
        self.run_js(r"""
const row=fixture();core.stop(row,'2026-10-27T13:00:00Z');
const original=JSON.stringify(row),shared=database([]),tab=await controller(shared);
await tab.get('restore').handlers.change({target:{value:'synthetic',files:[{
 size:Buffer.byteLength(original),text:async()=>original}]}});await shared.idle();
const saved=shared.rows.get(row.id),backup=await tab.backup();
assert.deepEqual(saved.points,row.points);assert.deepEqual(saved.events,row.events);assert.deepEqual(saved.gaps,row.gaps);
assert.deepEqual(backup.points,row.points);assert.deepEqual(backup.events,row.events);assert.equal(JSON.stringify(row),original);
""", controller=True)

    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_actual_ui_saves_explicit_observation_separately_and_clears_fields(self):
        self.run_js(r"""
const seed=fixture(), shared=database([seed]), tab=await controller(shared);
await tab.select(seed.id);
tab.context.Date=class extends Date {
 constructor(...args){super(...(args.length?args:['2026-10-27T12:00:30Z']));}
 static now(){return Date.parse('2026-10-27T12:00:30Z');}
};
tab.get('observedAt').value='2026-10-27T21:00:03';
await tab.click('add');await shared.idle();
assert.equal(shared.rows.get(seed.id).events.length,1,'a partial declaration must not persist');
tab.get('timeUncertainty').value='12.5';
await tab.click('add');await shared.idle();
const event=shared.rows.get(seed.id).events[1];
assert.deepEqual(event.observation,{observed_at:'2026-10-27T12:00:03.000Z',uncertainty_seconds:12.5});
assert(Date.parse(event.time)>Date.parse(event.observation.observed_at));
assert.equal(tab.get('observedAt').value,'');assert.equal(tab.get('timeUncertainty').value,'');
await tab.click('add');await shared.idle();
const exported=await tab.backup();
assert.deepEqual(exported.events[1],event);
assert.equal(Object.hasOwn(exported.events[2],'observation'),false);
""", controller=True)

    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_observation_roundtrip_keeps_recording_and_fix_clocks_and_rejects_bad_declarations(self):
        self.run_js(r"""
const assert=require('node:assert/strict'),c=require('./dashboard/field-core.js');
const s=c.createSession('observation-session-000001','2026-11-07T10:00:00Z');
c.recordPoint(s,{latitude:28,longitude:129,accuracy:5},'2026-11-07T10:00:19Z');
const event=c.event(s,{id:'observation-event-000001',type:'capture',species:'ハブ',count:2,owner:'self',
 time:'2026-11-07T10:00:20Z',position:s.points[0],
 observation:{observed_at:'2026-11-07T19:00:10+09:00',uncertainty_seconds:0}});
assert.deepEqual(event.observation,{observed_at:'2026-11-07T10:00:10.000Z',uncertainty_seconds:0});
assert.equal(event.time,'2026-11-07T10:00:20.000Z');
assert.equal(event.position.time,'2026-11-07T10:00:19.000Z');assert.equal(event.position.accuracy,5);
const good=JSON.parse(c.exportBackup(s));assert.equal(c.validateRestoredSession(good),good);
const basis=event.observation;
for(const invalid of [null,[],{...basis,uncertainty_seconds:-1},{...basis,uncertainty_seconds:'0'},
 {...basis,uncertainty_seconds:31536001},{...basis,source_authenticated:true},
 Object.assign(Object.create({observed_at:basis.observed_at}),{uncertainty_seconds:5,spoof:true}),
 {...basis,observed_at:'2026-11-07T10:00:10'},{...basis,observed_at:'2026-11-07T10:00:21Z'},
 {...basis,observed_at:'2026-11-07T09:59:59Z'},{...basis,observed_at:'2026-02-30T10:00:10Z'}]){
 const input=structuredClone(good);input.events[0].observation=invalid;
 const before=JSON.stringify(input);assert.throws(()=>c.validateRestoredSession(input));
 assert.equal(JSON.stringify(input),before);
}
""")

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
