"""Road, observed weather and measured air temperature are separate source events.

All fixtures are synthetic. No real owner GPS, Chat uploads or external climate API.
"""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class FieldConditionTests(unittest.TestCase):
    def node(self, source):
        r = subprocess.run(["node", "-"], input=source, cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_conditions_are_time_stamped_not_retrospective_and_not_biological_counts(self):
        self.node(r"""
const assert=require('node:assert/strict');
const c=require('./dashboard/field-core.js');
const s=c.createSession('synthetic-env-source-000001','2026-11-08T09:00:00Z');
const start=JSON.stringify(s);
assert.equal(c.recordCondition(s,{time:'2026-11-08T09:00:05Z',
 category:'road_surface',value:'dry'}),true);
assert.equal(c.recordCondition(s,{time:'2026-11-08T09:00:10Z',
 category:'weather',value:'rain'}),true);
assert.equal(c.recordCondition(s,{time:'2026-11-08T09:00:15Z',
 category:'air_temperature',value:23.5}),true);
c.event(s,{id:'synthetic-habu-capture-0001',time:'2026-11-08T09:00:20Z',
 type:'capture',species:'ハブ',owner:'self',count:1});
const capture=c.summary(s).reduce((x,n)=>x+n.ownerHabuCaptures,0);
assert.equal(capture,1);
assert.deepEqual(s.conditions.map(x=>x.source),['owner_visual','owner_visual','thermometer']);
assert.deepEqual(s.conditions.map(x=>x.category),['road_surface','weather','air_temperature']);
assert.equal(s.events.length,1);
const text=c.logfile(s);
assert.match(text,/2026\/11\/08 18:00:05\n環境観測\n路面: ドライ（本人目視）/);
assert.match(text,/天気: 雨（本人目視）/);
assert.match(text,/気温（温度計で実測）: 23.5℃/);
assert(!text.includes('気温（推定）'));
assert.equal(s.points.length,0,'conditions must not invent GPS fixes');
c.stop(s,'2026-11-08T09:05:00Z');
const backup=c.exportBackup(s),roundtrip=JSON.parse(backup);
assert.equal(c.validateRestoredSession(roundtrip),roundtrip);
assert.deepEqual(roundtrip.conditions,s.conditions);
assert(!c.gpx(s).includes('<trkpt'));
const legacy=JSON.parse(start);c.stop(legacy,'2026-11-08T09:02:00Z');
delete legacy.conditions;
assert.equal(c.validateRestoredSession(legacy),legacy,
  'legacy saved sessions without conditions must be accepted without mutation');
""")


    def test_event_and_conditions_bind_only_relevant_measured_gps(self):
        self.node(r"""
const assert=require('node:assert/strict'), c=require('./dashboard/field-core.js');
const s=c.createSession('synthetic-gps-context-000001','2026-11-08T10:00:00Z');
const t='2026-11-08T10:00:15Z';
assert.equal(c.measuredPositionAt(s,t),null);
c.recordPoint(s,{latitude:28.12345678,longitude:129.3456789,accuracy:7.5},'2026-11-08T10:00:10Z');
const fix=c.measuredPositionAt(s,t);
assert.equal(fix.lat,28.12345678);
assert.equal(fix.lon,129.3456789);
assert.equal(fix.accuracy,7.5);
assert.equal(fix.time,'2026-11-08T10:00:10.000Z');
c.recordCondition(s,{time:t,category:'road_surface',value:'wet',position:fix});
c.event(s,{time:'2026-11-08T10:00:16Z',id:'synthetic-capture-00000001',
  type:'capture',species:'ハブ',owner:'self',count:1,position:fix});
assert(c.logfile(s).includes('28.12345678\n129.3456789'));
assert.equal(s.conditions[0].position.time,fix.time);
assert.equal(s.events[0].position.time,fix.time);
assert.equal(c.measuredPositionAt(s,'2026-11-08T10:01:50Z'),null,
  'never attach a 100-second-old fix');
assert.equal(c.measuredPositionAt(s,'2026-11-08T10:00:01Z'),null,
  'never use a future measurement');
const before=JSON.stringify(s);
for(const wrong of [
 {...fix,lat:28.4444},
 {...fix,time:'2026-11-08T10:00:17Z'},
 {...fix,accuracy:999}
]){
 assert.throws(()=>c.recordCondition(s,{
  time:'2026-11-08T10:00:18Z',category:'weather',value:'rain',position:wrong
 }));
 assert.equal(JSON.stringify(s),before,'source cannot change on invalid GPS');
}
c.markGap(s,'2026-11-08T10:00:20Z','GPS停止');
assert.equal(c.measuredPositionAt(s,'2026-11-08T10:00:21Z'),null);
assert.equal(c.recordCondition(s,{time:'2026-11-08T10:00:21Z',
 category:'weather',value:'rain'}),true);
assert.equal(s.conditions.at(-1).position,undefined);
assert.match(c.logfile(s),/位置: 未取得/);
c.recordPoint(s,{latitude:28.100001,longitude:129.100001,accuracy:9},'2026-11-08T10:00:30Z');
c.stop(s,'2026-11-08T10:01:10Z');
// Restored session contains future points relative to its earlier observations.
const backup=JSON.parse(c.exportBackup(s));
assert.equal(backup.conditions[0].position.lat,28.12345678);
assert.equal(backup.events[0].position.lon,129.3456789);
assert.equal(c.summary(backup).reduce((n,x)=>n+x.ownerHabuCaptures,0),1);
assert.equal(c.gpx(backup).match(/<trkpt /g).length,2);
""")

    def test_real_controller_attaches_last_recorded_fix_to_event_and_road_status(self):
        from tests.test_field_writer_concurrency import HARNESS
        anchor="vm.runInNewContext(source,context,{filename:'field-app.js'});await shared.idle();"
        assert anchor in HARNESS
        setup=r"""const road=get('conditionRoad');
road.dataset={conditionCategory:'road_surface',conditionValue:'wet'};
road.textContent='濡れ';
context.document.querySelectorAll=selector=>
 selector==='[data-condition-category]'?[road]:[];
"""
        script=HARNESS.replace(anchor,setup+anchor)
        script+=r"""
(async()=>{
 const shared=database([fixture(false)]),tab=await controller(shared);
 await tab.click('gpsStart');
 tab.fix(28.125);await shared.idle();
 await tab.get('conditionRoad').handlers.click();await shared.idle();
 tab.get('type').value='capture';tab.get('species').value='ハブ';tab.get('count').value='1';
 await tab.click('add');await shared.idle();
 const row=shared.rows.get('synthetic-session-0000001');
 assert.equal(row.points.length,1);
 assert.equal(row.events.at(-1).position.lat,28.125);
 assert.equal(row.conditions.at(-1).position.lat,28.125);
 assert.equal(row.events.at(-1).position.accuracy,5);
 assert.equal(row.events.at(-1).position.time,row.points[0].time);
 assert.equal(row.conditions.at(-1).position.time,row.points[0].time);
 assert.match(core.logfile(row),/GPS測位時刻:/);
 assert.match(core.logfile(row),/28.125/);
 assert.equal(core.summary(row).reduce((n,x)=>n+x.ownerHabuCaptures,0),1);
 })().catch(e=>{console.error(e);process.exitCode=1;});
"""
        self.node(script)

    def test_invalid_or_unmeasured_climate_is_not_silently_admitted(self):
        self.node(r"""
const assert=require('node:assert/strict'),c=require('./dashboard/field-core.js');
const s=c.createSession('synthetic-env-reject-000001','2026-11-08T09:00:00Z');
for(const input of [
 {category:'air_temperature',value:'23.5'},
 {category:'air_temperature',value:null},
 {category:'air_temperature',value:61},
 {category:'air_temperature',value:-31},
 {category:'air_temperature',value:NaN},
 {category:'road_surface',value:'unknown'},
 {category:'weather',value:'predicted'},
 {category:'weather',value:'rain',source:'thermometer'},
 {category:'road_surface',value:'wet',time:'2026-11-08T08:59:59Z'},
]){
 const before=JSON.stringify(s);
 assert.throws(()=>c.recordCondition(s,{time:'2026-11-08T09:01:00Z',...input}));
 assert.equal(JSON.stringify(s),before);
}
assert.equal(s.conditions.length,0);
c.recordCondition(s,{time:'2026-11-08T09:02:00Z',category:'weather',value:'cloudy'});
c.stop(s,'2026-11-08T09:10:00Z');
for(const mutate of [
 x=>x.conditions[0].source='forecast',
 x=>x.conditions[0].value='bad',
 x=>x.conditions[0].time='2026-11-08T08:59:59Z',
 x=>x.conditions[0].value=999,
]){
 const copy=structuredClone(s);mutate(copy);const before=JSON.stringify(copy);
 assert.throws(()=>c.validateRestoredSession(copy));
 assert.equal(JSON.stringify(copy),before,'rejected backup must remain byte-for-byte intact');
}
""")

    def test_intake_preserves_same_second_conditions_without_fake_capture_conflicts(self):
        self.node(r"""
const assert=require('node:assert/strict'),parse=require('./dashboard/intake-core.js').parse;
const log=[
 'ハブログ','2026/11/08 19:00:00','エリア探索開始',
 '2026/11/08 19:00:00','環境観測','路面: ドライ（本人目視）',
 '2026/11/08 19:01:00','環境観測','天気: 雨（本人目視）',
 '2026/11/08 19:02:00','捕獲','1匹','ハブ','捕獲者: 本人',
 '2026/11/08 19:02:00','環境観測','気温（温度計で実測）: 22.5℃',
 '2026/11/08 19:05:00','エリア探索終了'
].join('\n');
const result=parse(log);
assert.deepEqual(result.problems,[]);
assert.equal(result.nights.length,1);
assert.equal(result.nights[0].captureHints,1);
assert.equal(result.nights[0].starts,1);
assert.equal(result.nights[0].ends,1);
assert.equal(result.nights[0].ambiguousTimes,0);
const both=log+'\n2026/11/08 19:02:00\n目撃\n1匹\nアカマタ\n';
assert(parse(both).nights[0].ambiguousTimes>0,
 'two distinct fauna reactions in one timestamp still require review');
""")

    def test_real_mobile_controller_commits_condition_taps_to_existing_idb_store(self):
        from tests.test_field_writer_concurrency import HARNESS
        anchor="vm.runInNewContext(source,context,{filename:'field-app.js'});await shared.idle();"
        assert anchor in HARNESS
        setup=r"""const road=get('conditionRoad'),weather=get('conditionWeather');
road.dataset={conditionCategory:'road_surface',conditionValue:'dry'};
road.textContent='ドライ';
weather.dataset={conditionCategory:'weather',conditionValue:'rain'};
weather.textContent='雨';
context.document.querySelectorAll=selector=>
 selector==='[data-condition-category]'?[road,weather]:[];
"""
        script=HARNESS.replace(anchor,setup+anchor)
        script+=r"""
(async()=>{
const shared=database([fixture(false)]),tab=await controller(shared);
await tab.get('conditionRoad').handlers.click();await shared.idle();
await tab.get('conditionWeather').handlers.click();await shared.idle();
tab.get('airTemperatureC').value='23.5';
await tab.click('recordTemperature');await shared.idle();
const row=shared.rows.get('synthetic-session-0000001');
assert.equal(row.events.length,1,'conditions are not fauna observations');
assert.deepEqual(row.conditions.map(x=>x.category),
 ['road_surface','weather','air_temperature']);
assert.equal(row.conditions[2].value,23.5);
assert.equal(row.conditions[2].source,'thermometer');
assert.match(core.logfile(row),/路面: ドライ/);
assert.match(core.logfile(row),/気温（温度計で実測）: 23.5℃/);
assert.equal(core.summary(row).reduce((x,n)=>x+n.ownerHabuCaptures,0),0);
const old=JSON.stringify(row);
await tab.click('backup');
assert.equal(JSON.stringify(shared.rows.get(row.id)),old);
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        self.node(script)

    def test_field_ui_has_optional_quick_road_weather_and_actual_temperature_controls(self):
        html=(ROOT/"dashboard/field.html").read_text(encoding="utf-8")
        app=(ROOT/"dashboard/field-app.js").read_text(encoding="utf-8")
        native=(ROOT/"mobile/ios/HabuFieldRecorder/ContentView.swift").read_text(encoding="utf-8")
        exporter=(ROOT/"mobile/ios/HabuFieldRecorder/HabuLogExporter.swift").read_text(encoding="utf-8")
        for field in ("conditionPanel","airTemperatureC","recordTemperature","conditionState"):
            self.assertIn(f'id="{field}"',html)
        for choice in ("dry","damp","wet","puddle"):
            self.assertIn(f'data-condition-value="{choice}"',html)
        for choice in ("clear","cloudy","rain","fog"):
            self.assertIn(f'data-condition-value="{choice}"',html)
        self.assertIn("core.recordCondition(session",app)
        self.assertIn("await persist()",app)
        self.assertIn('DisclosureGroup("路面・天気・実測気温（必要なときだけ）")',native)
        self.assertIn('func addCondition(category: String', 
                      (ROOT/"mobile/ios/HabuFieldRecorder/BackgroundTrackRecorder.swift").read_text(encoding="utf-8"))
        self.assertIn('case "condition":',exporter)
        self.assertIn('record.conditionSource == "thermometer"',exporter)
        self.assertNotIn("URLSession",exporter)


if __name__=="__main__":
    unittest.main()
