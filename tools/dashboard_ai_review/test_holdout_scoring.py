"""Scoring-contract tests for all 40 blind synthetic model calls (no network)."""
from __future__ import annotations

import json
import unittest

import holdout_v1
import measure_holdout


DATA = {row["path"]: row for row in holdout_v1.instances()}


def correct_synthetic_reply(path, patch):
    item = DATA[path]
    if item["label"] == "negative":
        return json.dumps({"findings": []})
    index = measure_holdout.logic_line(item["source"])
    code = item["source"].splitlines()[index - 1].strip()[:140]
    return json.dumps({"findings": [{
        "path": path, "line": index, "code_quote": code,
        "problem": "This yields a provably incorrect synthetic result",
        "impact": "The documented input violates the requirement",
    }]})


class FrozenHoldoutScoringTests(unittest.TestCase):
    def test_all_forty_oracle_responses_are_distinguishable(self):
        r = measure_holdout.score(model_call=correct_synthetic_reply)
        self.assertEqual(r["completed"], 40)
        self.assertEqual(r["possible_anchored_bug_cases"], 20)
        self.assertEqual(r["clean_unflagged_cases"], 20)
        self.assertEqual(r["clean_false_alert_cases"], 0)
        self.assertEqual(r["proxy_gate"], "PROVISIONAL")
        self.assertEqual(r["formal_semantic_validation"], "NOT_DONE")

    def test_same_model_saying_everything_is_safe_fails_recall(self):
        r = measure_holdout.score(
            model_call=lambda path, patch: json.dumps({"findings": []})
        )
        self.assertEqual(r["completed"], 40)
        self.assertEqual(r["possible_anchored_bug_cases"], 0)
        self.assertEqual(r["clean_unflagged_cases"], 20)
        self.assertEqual(r["proxy_gate"], "HOLD")

    def test_two_false_alerts_on_clean_code_fail_precision(self):
        clean_paths = [
            c["path"] for c in holdout_v1.instances() if c["label"] == "negative"
        ][:2]

        def model(path, patch):
            if path in clean_paths:
                item = DATA[path]
                idx = measure_holdout.logic_line(item["source"])
                return json.dumps({"findings": [{
                    "path": path, "line": idx,
                    "code_quote": item["source"].splitlines()[idx - 1].strip()[:140],
                    "problem": "Imaginary error on correct synthetic implementation",
                    "impact": "No actual violating input exists for this code",
                }]})
            return correct_synthetic_reply(path, patch)
        r = measure_holdout.score(model_call=model)
        self.assertEqual(r["clean_false_alert_cases"], 2)
        self.assertEqual(r["proxy_gate"], "HOLD")
        self.assertGreater(r["clean_false_alert_rate"], 0.05)

    def test_one_malformed_reply_is_incomplete_not_a_correct_zero(self):
        broken = holdout_v1.instances()[0]["path"]
        def model(path, patch):
            return "{not a valid model reply" if path == broken else correct_synthetic_reply(path, patch)
        r = measure_holdout.score(model_call=model)
        self.assertEqual(r["completed"], 39)
        self.assertEqual(r["incomplete"], 1)
        self.assertEqual(r["proxy_gate"], "INCOMPLETE")
        self.assertEqual(len(r["cases"]), 40)

    def test_quote_from_unrelated_line_does_not_detect_known_bug(self):
        target = holdout_v1.instances()[0]["path"]
        def model(path, patch):
            if path == target:
                item = DATA[path]
                return json.dumps({"findings": [{
                    "path": path, "line": 1,
                    "code_quote": item["source"].splitlines()[0][:80],
                    "problem": "An unrelated complaint attached to the requirement",
                    "impact": "This does not identify the defective return line",
                }]})
            return correct_synthetic_reply(path, patch)
        r = measure_holdout.score(model_call=model)
        self.assertEqual(r["possible_anchored_bug_cases"], 19)
        self.assertEqual(r["proxy_gate"], "PROVISIONAL")
        self.assertEqual(r["formal_semantic_validation"], "NOT_DONE")


if __name__ == "__main__":
    unittest.main()
