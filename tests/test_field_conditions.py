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
