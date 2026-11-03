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

    def test_diagnostics_preserve_exact_frozen_language_populations(self):
        result = measure_holdout.score(model_call=correct_synthetic_reply)
        stats = result["language_diagnostics"]
        self.assertEqual((stats["python"]["cases"], stats["js"]["cases"]), (24, 16))
        self.assertEqual((stats["python"]["known_bug_cases"],
                          stats["python"]["known_clean_cases"]), (12, 12))
        self.assertEqual((stats["js"]["known_bug_cases"],
                          stats["js"]["known_clean_cases"]), (8, 8))
        self.assertEqual(result["zero_finding_responses"], 20)
        self.assertFalse(result["all_completed_cases_flagged"])
        self.assertEqual(result["grounding_rejection_reasons"], {})
        self.assertEqual(sum(x["possible_bug_line_hits"] for x in stats.values()), 20)
        self.assertEqual(sum(x["raw_clean_alert_cases"] for x in stats.values()), 0)

    def test_all_case_warning_spam_is_reported_not_rebranded_as_accuracy(self):
        def untrustworthy_model(path, patch):
            item = DATA[path]
            code = item["source"].splitlines()[-1]
            return json.dumps({"findings": [{
                "path": path, "line": len(item["source"].splitlines()),
                "code_quote": code.strip()[:140],
                "problem": "A speculative defect without a concrete failing input",
                "impact": "An imagined failure might happen",
            }]})
        result = measure_holdout.score(model_call=untrustworthy_model)
        self.assertEqual(result["completed"], 40)
        self.assertEqual(result["zero_finding_responses"], 0)
        self.assertTrue(result["all_completed_cases_flagged"])
        self.assertEqual(result["clean_false_alert_cases"], 20)
        self.assertEqual(result["language_diagnostics"]["python"]["raw_clean_alert_cases"], 12)
        self.assertEqual(result["language_diagnostics"]["js"]["raw_clean_alert_cases"], 8)
        self.assertEqual(result["proxy_gate"], "HOLD")
        self.assertEqual(result["formal_semantic_validation"], "NOT_DONE")
        self.assertEqual(
            sum(result["grounding_rejection_reasons"].values()),
            result["grounding_rejected_findings"]
        )

    def test_pairwise_discrimination_reports_correct_silent_counterpart(self):
        good_model = measure_holdout.score(model_call=correct_synthetic_reply)
        self.assertEqual(good_model["paired_cases"], 20)
        self.assertEqual(good_model["pair_complete"], 20)
        self.assertEqual(good_model["pair_selective_raw_alerts"], 20)
        self.assertEqual(good_model["pair_selective_anchored_proxy"], 20)

        def alarm_everywhere(path, patch):
            item = DATA[path]
            index = measure_holdout.logic_line(item["source"])
            return json.dumps({"findings": [{
                "path": path,
                "line": index,
                "code_quote": item["source"].splitlines()[index - 1].strip()[:140],
                "problem": "This claims an error on every single code fixture",
                "impact": "The claim is not supported by the passing counterpart",
            }]})
        spam = measure_holdout.score(model_call=alarm_everywhere)
        self.assertEqual(spam["paired_cases"], 20)
        self.assertEqual(spam["pair_complete"], 20)
        self.assertEqual(spam["pair_selective_raw_alerts"], 0)
        self.assertEqual(spam["pair_selective_anchored_proxy"], 0)
        self.assertEqual(spam["clean_false_alert_cases"], 20)

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

    def test_raw_false_alarms_do_not_invalidate_precision_denominator(self):
        # An invalid citation on a clean fixture is a raw false alert,
        # but must not be counted as a published source-anchored finding.
        # This counterexample caught a mathematically invalid denominator
        # which mixed raw false alarms and grounded true-positive candidates.
        def model(path, patch):
            item = DATA[path]
            if item["label"] == "positive":
                return correct_synthetic_reply(path, patch)
            return json.dumps({"findings": [{
                "path": path, "line": measure_holdout.logic_line(item["source"]),
                "code_quote": "UNRELATED_SYNTHETIC_TEXT_NOT_ON_ANY_SOURCE_LINE",
                "problem": "A false alert about a correct implementation",
                "impact": "No witness input demonstrates a violation",
            }]})

        r = measure_holdout.score(model_call=model)
        self.assertEqual(r["completed"], 40)
        self.assertEqual(r["total_raw_findings"], 40)
        self.assertEqual(r["total_location_anchored_findings"], 20)
        self.assertEqual(r["grounding_rejected_findings"], 20)
        self.assertEqual(r["parse_dropped_findings"], 0)
        self.assertEqual(r["clean_false_alert_cases"], 20)
        self.assertEqual(r["anchored_clean_false_alert_cases"], 0)
        self.assertEqual(r["proxy_precision_ceiling"], 1.0)
        self.assertEqual(r["proxy_recall_ceiling"], 1.0)
        self.assertEqual(r["clean_false_alert_rate"], 1.0)
        self.assertEqual(r["proxy_gate"], "HOLD")
        self.assertEqual(r["formal_semantic_validation"], "NOT_DONE")

    def test_anchored_false_alarm_counts_in_precision_ceiling(self):
        clean_path = next(
            x["path"] for x in holdout_v1.instances()
            if x["label"] == "negative"
        )

        def model(path, patch):
            if path == clean_path:
                item = DATA[path]
                index = measure_holdout.logic_line(item["source"])
                return json.dumps({"findings": [{
                    "path": path, "line": index,
                    "code_quote": item["source"].splitlines()[index - 1].strip()[:140],
                    "problem": "Imaginary fault on a correctly implemented requirement",
                    "impact": "This is a synthetic false alarm",
                }]})
            return correct_synthetic_reply(path, patch)

        r = measure_holdout.score(model_call=model)
        self.assertEqual(r["total_location_anchored_findings"], 21)
        self.assertEqual(r["anchored_clean_false_alert_cases"], 1)
        self.assertEqual(r["clean_false_alert_cases"], 1)
        self.assertEqual(r["proxy_precision_ceiling"], round(20 / 21, 4))
        self.assertEqual(r["anchored_clean_false_alert_rate"], 0.05)
        self.assertEqual(r["formal_semantic_validation"], "NOT_DONE")

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
