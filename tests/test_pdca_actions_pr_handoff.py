"""The Actions PDCA bridge may discover report PRs but never create them."""
import importlib.util
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "habu_actions_pdca_entry", ROOT / "scripts" / "pdca_bridge.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConnectorHandoffTests(unittest.TestCase):
    def api_with_fake_request(self, rows):
        api = module.GitHubAPI("haji84/habuAI-private")
        api.default_branch = "main"
        calls = []

        def request(path="", method="GET", value=None):
            calls.append((method, path, value))
            self.assertEqual(method, "GET", "Actions must not POST /pulls")
            return rows

        api.request = request
        return api, calls

    def test_existing_connector_pr_is_reused_read_only(self):
        api, calls = self.api_with_fake_request(
            [{"html_url": "https://github.com/haji84/habuAI-private/pull/61"}])
        report = api.ensure_pr("pdca/run-abcdef", "2026-10-22")
        self.assertEqual(
            report, "https://github.com/haji84/habuAI-private/pull/61")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "GET")
        query = parse_qs(urlsplit("https://github.test/" + calls[0][1]).query)
        self.assertEqual(query["head"], ["haji84:pdca/run-abcdef"])
        self.assertEqual(query["base"], ["main"])

    def test_missing_pr_returns_branch_link_for_connector_handoff(self):
        api, calls = self.api_with_fake_request([])
        url = api.ensure_pr("pdca/run-abcdef", "2026-10-22")
        self.assertEqual(
            url, "https://github.com/haji84/habuAI-private/tree/pdca/run-abcdef")
        self.assertNotIn("/pull/", url)
        self.assertEqual(len(calls), 1)

    def test_command_and_poller_need_no_pr_write_grant(self):
        for relative in (".github/workflows/pdca-command.yml",
                         ".github/workflows/pdca-command-poller.yml"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("  pull-requests: read", content)
            self.assertNotIn("  pull-requests: write", content)


if __name__ == "__main__":
    unittest.main()
