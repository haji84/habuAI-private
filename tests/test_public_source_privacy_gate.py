"""Synthetic audit of public-source privacy. Never opens real owner raw files.

The production gate is scripts/check_public_source_privacy.sh and runs before
public release. It intentionally fails while personal original GPS sources
remain in tracked git data, even if a static page is Access protected.
"""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_public_source_privacy.sh"


class PublicSourcePrivacyGateTests(unittest.TestCase):
    def run_gate(self, sources):
        with tempfile.TemporaryDirectory(prefix="habu-privacy-fixture-") as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True,
                           capture_output=True, text=True)
            for name, content in sources.items():
                dest = repo / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True,
                           capture_output=True, text=True)
            return subprocess.run(["bash", str(GATE)], cwd=repo,
                                  capture_output=True, text=True, timeout=15)

    def test_allows_aggregated_counts_and_does_not_confuse_unlocated_sightings(self):
        r = self.run_gate({"data/raw/habu_owner_nights/2026/2026-11-08.json":
            json.dumps({"night":"2026-11-08","capture_count":2,"owner_confirmed":True})})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PUBLIC_SOURCE_AUDIT_PASS", r.stdout)

    def test_blocks_tracked_owner_original_even_without_coordinates(self):
        r = self.run_gate({"data/raw/habu_logs/2026/synthetic-owner-raw.txt":
                           "SYNTHETIC field diary without coordinates"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("PUBLIC_SOURCE_AUDIT_HOLD", r.stdout)
        self.assertNotIn("synthetic-owner-raw.txt", r.stdout)

    def test_blocks_coordinate_pairs_without_echoing_location_values(self):
        sample = "28.123456789 129.345678901"
        r = self.run_gate({"data/processed/individuals/synthetic.csv":
                           "location\n" + sample + "\n"})
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn(sample, r.stdout + r.stderr)
        self.assertNotIn("synthetic.csv", r.stdout + r.stderr)

    def test_blocks_keyed_coordinates_in_json_without_echoing_them(self):
        sample = '{"latitude":28.123456789,"longitude":129.345678901}'
        r = self.run_gate({"data/reconstructions/source.json": sample})
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn(sample, r.stdout + r.stderr)
        self.assertIn("PUBLIC_SOURCE_AUDIT_HOLD", r.stdout)

    def test_blocks_raw_gpx_even_if_empty_and_no_coordinates(self):
        r = self.run_gate({"data/raw/routes/synthetic.gpx": "<gpx></gpx>"})
        self.assertNotEqual(r.returncode, 0)

    def test_checks_are_wired_before_public_dashboard_build(self):
        bash = (ROOT / "scripts/build_cloudflare_pages.sh").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/hub-natural-dashboard.yml").read_text(encoding="utf-8")
        audit = "bash scripts/check_public_source_privacy.sh"
        self.assertIn(audit, bash)
        self.assertIn(audit, ci)
        self.assertLess(bash.index(audit), bash.index("python scripts/build_capture_dashboard.py"))
        self.assertLess(ci.index(audit), ci.index("Build aggregate-only dashboard"))
        self.assertIn("if: $"+"{{ false }}", ci)


if __name__ == "__main__":
    unittest.main()
