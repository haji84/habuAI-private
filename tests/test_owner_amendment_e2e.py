"""Approved presentation corrections must survive source reconciliation and the UI."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_capture_dashboard import CaptureDataError, build

ROOT = Path(__file__).resolve().parents[1]
NIGHT = "2026-10-24"


class OwnerAmendmentEndToEndTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.originals = {}
        for relative in [
            "dashboard/baseline_2026.json",
            "dashboard/owner_effort_2026-10-26.json",
            *[
                "data/reconstructions/habu_captures/"
                + date + "-owner-chat-dashboard-intake.json"
                for date in ("2026-10-22", NIGHT)
            ],
        ]:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            self.originals[relative] = (ROOT / relative).read_bytes()
            target.write_bytes(self.originals[relative])
        self.before = build(self.repo)

    def amendment(self, count=3, searched=True, **changes):
        payload = {
            "schema_version": "habu-owner-amendment-v1",
            "source": "user Habu log", "operational_date": NIGHT,
            "revision": 1, "owner_confirmed": True,
            "original_captures": 4, "original_search_performed": True,
            "capture_count": count, "search_performed": searched,
            "reason": "SYNTHETIC_APPROVED_CORRECTION",
        }
        payload.update(changes)
        path = self.repo / "data/raw/habu_owner_amendments/2026" / (
            payload["operational_date"] + ".json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def assert_sources_unchanged(self):
        for relative, original in self.originals.items():
            self.assertEqual((self.repo / relative).read_bytes(), original, relative)

    def assert_summary(self, data, total, positive, zero, nights, october):
        self.assertEqual(data["total"], total)
        self.assertEqual(data["asof"], "2026-10-24")
        self.assertEqual(data["baseline_cutoff"], "2026-10-20")
        self.assertEqual([n["night"] for n in data["nights"]],
                         [n["night"] for n in self.before["nights"]])
        self.assertEqual(data["months"][-1], {"key": "2026-10", "n": october, "cum": total})
        self.assertEqual(sum(m["n"] for m in data["months"]), total)
        self.assertEqual(sum(n["count"] for n in data["nights"]), total)
        effort = data["effort"]
        self.assertEqual((effort["positive_nights"], effort["zero_nights"],
                          effort["total_nights"]), (positive, zero, nights))
        self.assertAlmostEqual(effort["per_night_average"], total / nights, places=3)
        self.assertAlmostEqual(effort["capture_success_rate"], positive / nights, places=3)
        self.assertEqual(sum(m["nights"] for m in data["effort_months"]), nights)
        for month in data["effort_months"]:
            rows = [n for n in data["nights"] if n["month"] == month["key"]]
            searched = [n for n in rows if n["effort_confirmed"]]
            self.assertEqual(month["captures"], sum(n["count"] for n in rows))
            self.assertEqual(month["nights"], len(searched))
            self.assertEqual(month["positive_nights"], sum(n["count"] > 0 for n in searched))
            self.assertEqual(month["zero_nights"], sum(n["count"] == 0 for n in searched))
        self.assertTrue(effort["not_model_exposure"])
        self.assertTrue(effort["not_negative_training_labels"])
        stats = data["owner_chat_statistics"]
        self.assertEqual(stats, self.before["owner_chat_statistics"])
        self.assertEqual(stats["reported_capture_events"], 6)
        self.assertEqual(stats["formal_training_negative_from_review"], 0)
        self.assertEqual(stats["formal_training_positive_from_review"], 0)
        self.assert_sources_unchanged()

    def browser(self, payload, mode="refresh"):
        self.assertIsNotNone(shutil.which("node"), "Node is required for actual dashboard JS")
        html = (ROOT / "dashboard/index.html").read_text(encoding="utf-8")
        script = re.search(r"<script>\s*'use strict';(.*?)</script>", html, re.S).group(1)
        # Only browser I/O is stubbed; validator, refresh/upload controller,
        # render functions and event handlers are the actual production source.
        runner = r"""
const fs=require('fs'),vm=require('vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
class Element {
  constructor(){this.children=[];this.attrs={};this.handlers={};this.style={};
    this.classList={add(){},remove(){},toggle(){}};}
  set textContent(v){this.text=String(v);this.children=[];}
  get textContent(){return (this.text||'')+this.children.map(c=>c.textContent).join('');}
  append(...xs){this.children.push(...xs);}
  replaceChildren(...xs){this.text='';this.children=xs;}
  setAttribute(k,v){this.attrs[k]=String(v);}
  addEventListener(k,f){this.handlers[k]=f;}
}
const els=new Map(),get=id=>{if(!els.has(id))els.set(id,new Element());return els.get(id);};
get('snapshot').textContent=JSON.stringify(input.snapshot);
const context=vm.createContext({
  document:{getElementById:get,createElement:()=>new Element(),
    createElementNS:()=>new Element(),querySelectorAll:()=>[]},
  window:{innerWidth:1000,addEventListener(){}},navigator:{},
  console:{info(){}},alert(message){throw Error(message);},
  fetch:async()=>({ok:true,json:async()=>input.mode==='upload'?input.snapshot:input.payload})
});
(async()=>{
  vm.runInContext(input.script,context);
  await new Promise(resolve=>setImmediate(resolve));
  if(input.mode==='upload'){
    await get('fileInput').handlers.change({target:{
      files:[{text:async()=>JSON.stringify(input.payload)}],value:'test.json'}});
  } else { await vm.runInContext('refresh()',context); }
  const cal=get('calendar').children.find(e=>(e.attrs['aria-label']||'').startsWith('2026-10-24 '));
  const row=get('list').children.find(e=>e.textContent.startsWith('10月24日'));
  if(row)row.onclick();
  process.stdout.write(JSON.stringify({
    total:get('total').textContent,nights:get('effortTotal').textContent,
    positive:get('effortPositive').textContent,zero:get('effortZero').textContent,
    status:get('sourceStatus').textContent,calendar:cal&&cal.attrs['aria-label'],
    row:row&&row.textContent,detail:get('detail').textContent
  }));
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        proc = subprocess.run(
            ["node", "-e", runner],
            input=json.dumps({"snapshot": self.before, "payload": payload,
                              "script": script, "mode": mode}),
            text=True, encoding="utf-8", capture_output=True, timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_receipt_backed_capture_correction_reaches_refresh_and_upload(self):
        self.amendment()
        data = build(self.repo)
        self.assert_summary(data, 248, 86, 11, 97, 22)
        record = next(n for n in data["nights"] if n["night"] == NIGHT)
        self.assertEqual(record["effort_status"], "OWNER_AMENDED_CAPTURE")
        self.assertEqual(record["events"], 4)  # Original source event count.
        self.assertIn("訂正", record["status"])
        self.assertNotIn("会話記録が一致", record["status"])
        for mode in ("refresh", "upload"):
            with self.subTest(mode=mode):
                shown = self.browser(data, mode)
                self.assertEqual((shown["total"], shown["nights"]), ("248", "97"))
                self.assertIn("2026-10-24 3匹", shown["calendar"])
                self.assertIn("訂正", shown["detail"])
                self.assertNotIn("保存版", shown["status"])
        self.assertEqual(build(self.repo)["total"], 248)

    def test_receipt_backed_zero_correction_is_personal_effort_only(self):
        self.amendment(count=0)
        data = build(self.repo)
        self.assert_summary(data, 245, 85, 12, 97, 19)
        shown = self.browser(data)
        self.assertEqual((shown["total"], shown["positive"], shown["zero"]),
                         ("245", "85", "12"))
        self.assertIn("探索確認0匹", shown["calendar"])
        self.assertIn("探索済み・捕獲記録なし", shown["row"])

    def test_receipt_backed_not_search_correction_is_rendered_as_excluded(self):
        self.amendment(count=0, searched=False)
        data = build(self.repo)
        self.assert_summary(data, 245, 85, 11, 96, 19)
        shown = self.browser(data)
        self.assertEqual((shown["total"], shown["nights"]), ("245", "96"))
        self.assertIn("探索なし・集計対象外", shown["calendar"])
        self.assertIn("探索なし・集計対象外", shown["row"])
        self.assertNotIn("探索済み", shown["row"])

    def test_actual_browser_accepts_amendment_without_chat_receipt(self):
        for relative in self.originals:
            if relative.startswith("data/reconstructions/"):
                (self.repo / relative).unlink()
        self.amendment()
        shown = self.browser(build(self.repo))
        self.assertEqual(shown["total"], "248")
        self.assertNotIn("保存版", shown["status"])

    def test_unapproved_wrong_original_and_unknown_night_are_rejected(self):
        for changes, message in [
            ({"owner_confirmed": False}, "Unconfirmed"),
            ({"original_captures": 7}, "conflicts"),
            ({"original_search_performed": False}, "conflicts"),
            ({"operational_date": "2026-10-25", "original_captures": 0}, "conflicts"),
            ({"source": "untrusted"}, "Untrusted"),
        ]:
            with self.subTest(changes=changes):
                path = self.amendment(**changes)
                with self.assertRaisesRegex(CaptureDataError, message):
                    build(self.repo)
                path.unlink()
        self.assert_sources_unchanged()

    def test_amendment_cannot_hide_conflicting_canonical_base(self):
        folder = self.repo / "data/raw/habu_logs/2026"
        folder.mkdir(parents=True)
        (folder / "2026-10-24.json").write_text(json.dumps({
            "schema_version": "habu-night-log-v2", "source": "user Habu log",
            "operational_date": NIGHT, "events": [{
                "event_id": "synthetic-canonical", "type": "capture",
                "capture_owner": "self", "species": "Habu", "individual_count": 3,
                "time_local": "2026-10-24T20:00:00+09:00",
            }],
        }), encoding="utf-8")
        self.amendment()
        with self.assertRaisesRegex(CaptureDataError, "count disagreement"):
            build(self.repo)
        self.assert_sources_unchanged()

    def test_duplicate_amendment_is_rejected(self):
        path = self.amendment()
        duplicate = path.parent / "duplicate/2026" / path.name
        duplicate.parent.mkdir(parents=True)
        duplicate.write_bytes(path.read_bytes())
        with self.assertRaisesRegex(CaptureDataError, "Duplicate/mismatched"):
            build(self.repo)


if __name__ == "__main__":
    unittest.main()
