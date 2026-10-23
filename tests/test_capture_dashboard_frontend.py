"""Validate the actual browser JavaScript and embedded fallback snapshot."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "dashboard/index.html"


class DashboardBrowserSourceTests(unittest.TestCase):
    def test_embedded_snapshot_reconciles_april(self):
        text = HTML.read_text(encoding="utf-8")
        found = re.search(r'<script id="snapshot" type="application/json">(.*?)</script>', text, re.S)
        self.assertIsNotNone(found)
        snapshot = json.loads(found.group(1))
        self.assertEqual(snapshot["total"], 240)
        self.assertEqual(
            snapshot["owner_confirmed_monthly_counts"]["2026-04"]["status"],
            "OWNER_CONFIRMED",
        )
        self.assertEqual(
            snapshot["owner_confirmed_monthly_counts"]["2026-04"]["count"], 10
        )
        self.assertFalse(
            snapshot["owner_confirmed_monthly_counts"]["2026-04"][
                "independent_event_time_location_gpx_verification"
            ]
        )
        self.assertIn("4月10匹は本人確定集計", text)
        self.assertEqual(snapshot["months"][0]["n"], 10)
        self.assertEqual(sum(n["count"] for n in snapshot["nights"]
                             if n["month"] == "2026-04"), 10)
        self.assertEqual(sum(x["count"] for x in snapshot["undated_captures"]), 0)
        self.assertEqual(next(n["count"] for n in snapshot["nights"] if n["night"] == "2026-04-17"), 0)
        self.assertEqual(next(n["count"] for n in snapshot["nights"]
                              if n["night"] == "2026-04-28"), 1)
        self.assertEqual(next(n["count"] for n in snapshot["nights"]
                              if n["night"] == "2026-04-29"), 3)
        self.assertEqual(snapshot["undated_count"], 0)
        self.assertEqual(snapshot["undated_captures"], [])
        self.assertEqual(sum(m["n"] for m in snapshot["months"]), snapshot["total"])
        self.assertEqual(sum(n["count"] for n in snapshot["nights"]) +
                         snapshot["undated_count"], snapshot["total"])

    def test_undated_entry_is_visible_and_exported(self):
        text = HTML.read_text(encoding="utf-8")
        self.assertIn("日付未復元", text)
        self.assertIn("data.undated_captures||[]", text)
        self.assertIn("'日付未復元・'+n.month", text)
        self.assertIn("月別集計が不一致", text)

    @unittest.skipUnless(shutil.which("node"), "node not available in local interpreter")
    def test_browser_javascript_syntax(self):
        text = HTML.read_text(encoding="utf-8")
        found = re.search(r"<script>\s*'use strict';(.*?)</script>", text, re.S)
        self.assertIsNotNone(found)
        script = "'use strict';" + found.group(1)
        proc = subprocess.run(
            ["node", "--check"], input=script, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
