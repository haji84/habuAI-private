"""Exercise PUBLIC runner templates in the existing PR's no-model CI.

Only dummy synthetic cases. This suite does NOT create any repository, use
an external GitHub token, run Qwen, sign a real cohort, or score real quality.
"""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = (Path(__file__).resolve().parents[2] /
        "docs/qa/eval-bootstrap/public-runner")
VAULT = ROOT.parent / "private-vault"


def _load_public_tests():
    if not ROOT.is_dir() or not (ROOT / "tests/test_public_runner.py").is_file():
        raise RuntimeError("PUBLIC_EVALUATION_TEMPLATE_MISSING")
    sys.path.insert(0, str(ROOT))
    target = ROOT / "tests/test_public_runner.py"
    spec = importlib.util.spec_from_file_location(
        "_habu_bootstrap_public_runner_tests", target)
    if spec is None or spec.loader is None:
        raise RuntimeError("BOOTSTRAP_TEST_IMPORT_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicRunnerTemplateContractTests(unittest.TestCase):
    def test_public_actions_are_manual_standard_runner_and_read_only(self):
        yml = (ROOT / ".github/workflows/evaluate.yml").read_text("utf-8")
        self.assertIn("workflow_dispatch:", yml)
        self.assertIn("runs-on: ubuntu-24.04", yml)
        self.assertIn("permissions:\n  contents: read", yml)
        self.assertIn("persist-credentials: false", yml)
        self.assertIn("timeout-minutes: 90", yml)
        self.assertIn("GITHUB_REPOSITORY", yml)
        self.assertIn("haji84/habuAI-eval-runner", yml)
        self.assertNotIn("\n  push:", yml)
        self.assertNotIn("\n  pull_request:", yml)
        self.assertNotIn("pull_request_target:", yml)
        self.assertNotIn("upload-artifact@", yml)
        self.assertNotIn("secrets.", yml)
        self.assertNotIn("id-token: write", yml)
        self.assertNotIn("runs-on: [", yml)

    def test_new_vault_template_can_never_spend_private_actions_minutes(self):
        self.assertTrue((VAULT / "README.md").is_file())
        self.assertTrue((VAULT / ".gitignore").is_file())
        self.assertTrue((VAULT / "custody-policy.json").is_file())
        self.assertFalse((VAULT / ".github/workflows").exists())
        text = (VAULT / "README.md").read_text("utf-8")
        self.assertIn("PRIVATE", text)
        self.assertIn("DO NOT", text)
        self.assertIn("CUSTODY_NOT_INDEPENDENT", text)

    def test_no_private_answer_fields_are_used_by_public_runner_script(self):
        text = (ROOT / "run_public_eval.py").read_text("utf-8")
        self.assertIn("validate_public_packet(", text)
        self.assertIn("quality_qualified", text)
        self.assertNotIn("eval-vault.git", text)
        self.assertNotIn("github_pat_", text)
        self.assertNotIn("OPENAI_API_KEY", text)
        self.assertNotIn("github_token", text)

    def test_bootstrap_never_contains_real_eval_answers_or_encryption_keys(self):
        for p in ROOT.rglob("*.json"):
            raise AssertionError(f"No active public case packet should exist: {p}")
        self.assertFalse((ROOT / "cohort/public-packet.json").exists())
        self.assertFalse((VAULT / "encrypted").exists())


def load_tests(loader, tests, pattern):
    tests.addTests(loader.loadTestsFromModule(_load_public_tests()))
    return tests


if __name__ == "__main__":
    unittest.main()
