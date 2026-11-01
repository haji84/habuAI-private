"""Independent executable-oracle tests for fixed 40-case quality holdout v1.

Every 'bad' case must demonstrably violate its requirement on the witness
input, while its matched 'good' case must match the expected result. The
language model sees neither this test nor any label or oracle witness.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

import holdout_v1
from grounding import added_source_lines

# Git blob SHA1 is frozen independently of evaluated model output.
FROZEN_HOLDOUT_BLOB = "daac52dfed89cb946e736aed49ed109a56307ffa"


def fixture_result(case: dict):
    """Execute only trusted, hand-authored fixture source, never AI output."""
    if case["language"] == "python":
        namespace = {}
        exec(compile(case["source"], "<trusted-holdout-source>", "exec"), namespace)
        return namespace["check"](*case["args"])
    if case["language"] == "js":
        if not shutil.which("node"):
            raise RuntimeError("Node.js unavailable: JS fixture validation is mandatory")
        script = (
            case["source"]
            + '\nconst args=JSON.parse(process.argv[1]);\n'
            + 'process.stdout.write(JSON.stringify(check(...args)));\n'
        )
        proc = subprocess.run(
            ["node", "-e", script, json.dumps(case["args"], ensure_ascii=False)],
            text=True, capture_output=True, timeout=12,
        )
        if proc.returncode != 0:
            raise AssertionError(proc.stderr)
        return json.loads(proc.stdout)
    raise ValueError("Unexpected benchmark language")


class FrozenHoldoutV1Tests(unittest.TestCase):
    def test_fixture_bytes_are_immutable_without_new_review(self):
        raw = (Path(__file__).parent / "holdout_v1.py").read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        self.assertEqual(blob, FROZEN_HOLDOUT_BLOB)

    def test_20_pairs_are_balanced_and_blinded(self):
        cases = holdout_v1.instances()
        self.assertEqual(len(cases), 40)
        self.assertEqual(sum(x["label"] == "positive" for x in cases), 20)
        self.assertEqual(sum(x["label"] == "negative" for x in cases), 20)
        self.assertEqual(sum(x["language"] == "python" for x in cases), 24)
        self.assertEqual(sum(x["language"] == "js" for x in cases), 16)
        self.assertEqual(len({x["family"] for x in cases}), 20)
        self.assertEqual(len({x["path"] for x in cases}), 40)
        for case in cases:
            visible = holdout_v1.public_prompt_instance(case)
            self.assertEqual(set(visible), {"path", "patch"})
            self.assertNotIn("label", visible)
            self.assertNotIn("expected_good", visible)
            self.assertNotIn("args", visible)
            self.assertNotIn(case["family"], case["path"])
            added = added_source_lines(case["patch"])
            self.assertEqual(
                [added[n] for n in sorted(added)], case["source"].splitlines()
            )

    def test_all_40_sources_have_demonstrable_good_bad_behavior(self):
        groups = {}
        for case in holdout_v1.instances():
            groups.setdefault(case["family"], {})[case["label"]] = case
        self.assertEqual(len(groups), 20)
        for family, pair in groups.items():
            with self.subTest(family=family):
                self.assertEqual(set(pair), {"positive", "negative"})
                bad = pair["positive"]
                good = pair["negative"]
                self.assertEqual(bad["args"], good["args"])
                self.assertEqual(bad["expected_good"], good["expected_good"])
                self.assertNotEqual(
                    fixture_result(bad), bad["expected_good"],
                    f"{family}: positive label must have failing witness",
                )
                self.assertEqual(
                    fixture_result(good), good["expected_good"],
                    f"{family}: negative must pass its witness",
                )


if __name__ == "__main__":
    unittest.main()
