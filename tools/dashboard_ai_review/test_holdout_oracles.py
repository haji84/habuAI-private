"""Independent execution witness for each of 20 frozen positive/negative pairs.

Only six-line-or-smaller trusted synthetic functions from holdout_v1 are run.
No model text, project code, private records, GPS, or network are executed.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import unittest

from grounding import added_source_lines
from holdout_v1 import PAIRS, instances, public_prompt_instance

FAMILIES = (
    "capture_kind", "species_filter", "seven_hour", "latitude_range",
    "longitude_range", "event_id_dedup", "boolean_not_count",
    "confirmed_zero", "exposure_not_inferred", "path_traversal",
    "capture_limit", "digest_equality", "gap_inclusive", "save_ack",
    "free_route_export", "owner_confirmation_boolean", "digest_hex",
    "distinct_same_time", "monthly_sum", "privacy_export",
)


class FrozenHoldoutOracles(unittest.TestCase):
    def test_fixed_inventory_and_label_blinding(self):
        self.assertEqual(tuple(x["key"] for x in PAIRS), FAMILIES)
        self.assertEqual(len(PAIRS), 20)
        entries = instances()
        self.assertEqual(len(entries), 40)
        self.assertEqual({x["label"] for x in entries}, {"positive", "negative"})
        self.assertEqual(sum(x["label"] == "positive" for x in entries), 20)
        self.assertEqual(sum(x["label"] == "negative" for x in entries), 20)
        self.assertEqual(len(set(x["path"] for x in entries)), 40)
        for e in entries:
            public = public_prompt_instance(e)
            self.assertEqual(set(public), {"path", "patch"})
            self.assertNotIn("expected_good", json.dumps(public))
            self.assertNotIn('"label"', json.dumps(public))
            self.assertNotIn('"args"', json.dumps(public))
            self.assertEqual(public["path"], e["path"])
            additions = added_source_lines(e["patch"])
            self.assertEqual([additions[i] for i in sorted(additions)],
                             e["source"].splitlines())

    def test_all_twelve_python_pairs_have_real_bad_good_counterexamples(self):
        python_cases = [x for x in PAIRS if x["lang"] == "python"]
        self.assertEqual(len(python_cases), 12)
        for row in python_cases:
            with self.subTest(family=row["key"]):
                actual = {}
                for variant in ("bad", "good"):
                    # Code is a fixed reviewed tiny fixture; NOT LLM output.
                    ns = {"__builtins__": __builtins__}
                    exec(compile(row[variant], "<trusted-fixed-holdout>", "exec"), ns)
                    args = copy.deepcopy(row["args"])
                    output = ns["check"](*args)
                    actual[variant] = output
                self.assertEqual(actual["good"], row["expected"])
                self.assertIs(type(actual["good"]), type(row["expected"]))
                self.assertNotEqual(actual["bad"], row["expected"])

    @unittest.skipUnless(shutil.which("node"), "node required for fixed JS witness")
    def test_all_eight_js_pairs_have_real_bad_good_counterexamples(self):
        js_cases = [x for x in PAIRS if x["lang"] == "js"]
        self.assertEqual(len(js_cases), 8)
        for row in js_cases:
            with self.subTest(family=row["key"]):
                actual = {}
                for variant in ("bad", "good"):
                    script = (row[variant] + "\n"
                              + "console.log(JSON.stringify(check(..."
                              + json.dumps(row["args"], ensure_ascii=False)
                              + ")));\n")
                    result = subprocess.run(
                        ["node", "-e", script], capture_output=True, text=True,
                        check=False, timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    actual[variant] = json.loads(result.stdout.strip())
                self.assertEqual(actual["good"], row["expected"])
                self.assertNotEqual(actual["bad"], row["expected"])


if __name__ == "__main__":
    unittest.main()
