"""First Pages deployment security gates. No external requests are made."""
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import verify_pages_access as access

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts/build_cloudflare_pages.sh"


class PagesBootstrapTests(unittest.TestCase):
    def run_build(self, *, enabled=False, previews_disabled=False, bootstrap=False):
        environment = dict(os.environ)
        for key in ("HUB_NATURAL_ACCESS_VERIFIED", "HUB_NATURAL_PREVIEWS_DISABLED",
                    "HUB_NATURAL_BOOTSTRAP_DEPLOYMENT", "HUB_NATURAL_PRODUCTION_URL"):
            environment.pop(key, None)
        if enabled:
            environment["HUB_NATURAL_ACCESS_VERIFIED"] = "true"
        if previews_disabled:
            environment["HUB_NATURAL_PREVIEWS_DISABLED"] = "true"
        if bootstrap:
            environment["HUB_NATURAL_BOOTSTRAP_DEPLOYMENT"] = "true"
        return subprocess.run(
            ["bash", str(BUILD_SCRIPT)],
            cwd=ROOT, env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10,
            check=False,
        )

    def test_bash_syntax(self):
        p = subprocess.run(["bash", "-n", str(BUILD_SCRIPT)], check=False)
        self.assertEqual(p.returncode, 0)

    def test_no_access_approval_blocks(self):
        result = self.run_build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED: Explicit Cloudflare Access approval", result.stdout)

    def test_preview_deployments_required_disabled(self):
        result = self.run_build(enabled=True, bootstrap=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED: Preview deployments must be disabled", result.stdout)

    def test_followup_needs_production_url(self):
        result = self.run_build(enabled=True, previews_disabled=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED: Production URL is required", result.stdout)

    def test_production_only_cli(self):
        with patch.object(sys, "argv", ["check", "--production",
                                        "https://hub-natural-private.pages.dev/"]):
            with patch.object(access, "verify") as verify:
                access.main()
                verify.assert_called_once_with("https://hub-natural-private.pages.dev/")


if __name__ == "__main__":
    unittest.main()
