"""Qwen four follow-ups plus independent capture-record integrity tests.

All observations, owners and timestamps in this file are synthetic.
The tests never open private GPS files or use network APIs.
"""
from html.parser import HTMLParser
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ButtonLabels(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons = []
        self.current = None
        self.svg_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "button":
            if self.current is not None:
                raise AssertionError("Nested HTML buttons")
            self.current = {"aria": dict(attrs).get("aria-label", ""), "text": []}
        elif tag == "svg" and self.current is not None:
            self.svg_depth += 1

    def handle_data(self, data):
        if self.current is not None and self.svg_depth == 0:
            self.current["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "svg" and self.current is not None:
            self.svg_depth = max(0, self.svg_depth - 1)
        elif tag == "button" and self.current is not None:
            self.buttons.append(self.current)
            self.current = None


class QwenFollowupTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_jst_wall_clock_and_offest_input_not_silently_accepted(self):
        js = r"""
const assert=require('node:assert/strict');
const m=require('./dashboard/intake-core.js');
assert.equal(m.nightOf(2028,2,29,6,59),'2028-02-28');
assert.equal(m.nightOf(2027,2,29,9,0),null);
assert.equal(m.timestamp('2026/11/01 06:59').night,'2026-10-31');
assert.equal(m.timestamp('2026/11/01 07:00').night,'2026-11-01');
assert.equal(m.timestamp('2026-11-01T06:59:00+09:00'),null);
const p=m.parse('2026-11-01T06:59:00+09:00\n捕獲\nハブ');
assert.equal(p.uniqueBlocks,0);
assert(p.problems.some(x=>x.includes('日時に紐づかない')));
console.log('JST_WALL_CLOCK_AND_UNKNOWN_OFFSET_FAIL_CLOSED');
"""
        for tz in ("UTC", "Asia/Tokyo", "America/Los_Angeles"):
            with self.subTest(tz=tz):
                self.run_node(js, tz)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_same_time_distinct_events_and_exact_duplicate_warning(self):
        js = r"""
const assert=require('node:assert/strict');
const m=require('./dashboard/intake-core.js');
const t='2026/11/01 23:30';
const s=['ハブログ',
 t,'捕獲','ハブ','1匹',
 t,'捕獲','ハブ','1匹',
 t,'目撃','アカマタ','1匹',
 t,'捕獲','ハブ','2匹'].join('\n');
const p=m.parse(s);
assert.equal(p.blocks,4);
assert.equal(p.uniqueBlocks,3);
assert.equal(p.exactRepeats,1);
assert.equal(p.nights.length,1);
assert.equal(p.nights[0].captureHints,2);
assert.equal(p.nights[0].sightings,1);
assert.equal(p.nights[0].ambiguousTimes,3);
assert(p.warning.includes('本人の確定捕獲数ではありません'));
console.log('SAME_TIME_DISTINCT_EVENT_PRESERVATION');
"""
        self.run_node(js)

    def test_static_and_dynamic_dashboard_buttons_have_accessible_names(self):
        html = (ROOT / "dashboard/index.html").read_text(encoding="utf-8")
        parser = ButtonLabels()
        parser.feed(html)
        self.assertGreaterEqual(len(parser.buttons), 10)
        for number, button in enumerate(parser.buttons, start=1):
            self.assertTrue(
                button["aria"].strip() or "".join(button["text"]).strip(),
                f"HTML button #{number} lacks an accessible name",
            )
        # JS-created bar/calendar buttons have explicit aria-label;
        # month and history buttons contain visible text.
        self.assertIn("b.setAttribute('aria-label',b.title)", html)
        self.assertIn("b.setAttribute('aria-label',date+", html)
        self.assertIn("node('button','month-tab'", html)
        self.assertIn("node('button','entry')", html)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_independent_capture_owner_must_not_default_unknown_to_self(self):
        js = r"""
const assert=require('node:assert/strict');
const c=require('./dashboard/field-core.js');
const s=c.createSession('owner-contract-2026-a01','2026-11-01T20:00:00Z');
const base={id:'test-unknown-owner-00001',type:'capture',
 species:'ハブ',count:1,time:'2026-11-01T20:01:00Z'};
assert.throws(()=>c.event(s,{...base,owner:'unknown'}),/捕獲者/);
assert.throws(()=>c.event(s,{...base,id:'test-missing-owner-00001'}),/捕獲者/);
assert.equal(s.events.length,0);
assert.equal(c.summary(s)[0].ownerHabuCaptures,0);
c.event(s,{...base,id:'test-other-owner-000001',owner:'other'});
assert.equal(c.summary(s)[0].ownerHabuCaptures,0);
c.event(s,{...base,id:'test-self-owner-0000001',owner:'self'});
assert.equal(c.summary(s)[0].ownerHabuCaptures,1);
console.log('OWNER_REJECTS_UNKNOWN_NO_FALSE_SELF_CAPTURE');
"""
        self.run_node(js)

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_independent_stale_gps_fix_before_session_start_is_rejected(self):
        js = r"""
const assert=require('node:assert/strict');
const c=require('./dashboard/field-core.js');
const s=c.createSession('gps-prestart-contract-001','2026-11-01T20:00:00Z');
const pos={latitude:0,longitude:0,accuracy:5};
assert.throws(()=>c.recordPoint(s,pos,'2026-11-01T19:59:59Z'),/探索開始前/);
assert.equal(s.points.length,0);
assert.equal(c.recordPoint(s,pos,'2026-11-01T20:00:00Z'),true);
assert.equal(s.points.length,1);
console.log('PRESTART_GPS_NOT_RECORDED');
"""
        self.run_node(js)

    def run_node(self, js, tz="UTC"):
        env = dict(os.environ, TZ=tz)
        proc = subprocess.run(
            ["node", "-e", js], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
