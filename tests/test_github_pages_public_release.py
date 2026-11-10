"""Synthetic/aggregate-only regression gate for HUB NATURAL GitHub Pages output."""
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/"dashboard/public-release"
ALLOWLIST={"index.html","data/public_summary.json"}
JSON_KEYS={
    "asof","capture_total","capture_total_status","effort_nights",
    "models","months","non_search_days","official_model_status",
    "owner_confirmation_day_jst","owner_confirmation_scope",
    "owner_reported_total","publication_scope","schema_version",
    "total_difference","year",
}

class PublicReleaseTests(unittest.TestCase):
    def test_exact_release_file_allowlist(self):
        actual={p.relative_to(RELEASE).as_posix() for p in RELEASE.rglob("*") if p.is_file()}
        self.assertEqual(actual,ALLOWLIST)
        self.assertFalse(any(p.is_symlink() for p in RELEASE.rglob("*")))

    def test_aggregate_sums_reconcile(self):
        data=json.loads((RELEASE/"data/public_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data),JSON_KEYS)
        self.assertEqual(data["capture_total"],sum(x["captures"] for x in data["months"]))
        self.assertEqual(data["capture_total"]-data["owner_reported_total"],data["total_difference"])
        self.assertTrue(all(set(x)=={"month","captures","cumulative","effort_nights","positive_nights","zero_nights"} for x in data["months"]))
        self.assertTrue(all(isinstance(x["captures"],int) and x["captures"]>=0 for x in data["months"]))

    def test_browser_csp_and_no_network(self):
        html=(RELEASE/"index.html").read_text(encoding="utf-8")
        self.assertIn('Content-Security-Policy',html)
        self.assertIn("connect-src 'none'",html)
        self.assertNotIn('fetch(',html.lower())
        self.assertNotIn('https://',html.lower())
        self.assertNotIn('navigator.geolocation',html.lower())

    def test_no_precision_source_in_public_output(self):
        for path in [RELEASE/"index.html",RELEASE/"data/public_summary.json"]:
            text=path.read_text(encoding="utf-8")
            self.assertNotRegex(text,re.compile(r"(?<!\\d)(?:28|129)\\.\\d{6,}"))
            for term in ("GPX原本","/ハブAI/","OPENAI_API_KEY","PRIVATE_KEY","AES_KEY","capture_lat","capture_lon"):
                self.assertNotIn(term,text)

if __name__=="__main__":
    unittest.main()
