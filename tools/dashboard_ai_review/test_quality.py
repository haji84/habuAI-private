"""Model-free calibration contract tests. Real CPU inference is a separate gate."""
import json
import unittest

import quality
import review
from grounding import added_source_lines


def fake_parse(raw: str, path: str) -> list[dict]:
    return [f for f in json.loads(raw)["findings"] if f.get("path") == path]


def synthetic_model(path: str, patch: str, model: str = review.MODEL,
                    segment_id: str | None = None) -> str:
    if path == "fixture/stale_fix.py":
        finding = {
            "path": path, "line": 4,
            "code_quote": "sample_time_ns >= tracking_start_ns - grace_period_ns",
            "problem": "Stale fixes before tracking start are permitted",
            "impact": "Old positions appear in current GPS tracks",
        }
    elif path == "fixture/owner.js":
        finding = {
            "path": path, "line": 2,
            "code_quote": "item.owner === 'other' ? 'other' : 'self'",
            "problem": "Unknown owner defaults to self",
            "impact": "A different person's capture is attributed to self",
        }
    else:
        return json.dumps({"findings": []})
    return json.dumps({"findings": [finding]})


class QualityCalibrationTests(unittest.TestCase):
    def test_fixture_identity_is_fixed_and_source_matches(self):
        self.assertEqual(quality.CASES[0]["patch"], review.QUALIFY_DIFF)
        self.assertEqual(len(quality.CASES), 6)
        self.assertEqual(sum(c["kind"] == "positive" for c in quality.CASES), 2)
        self.assertEqual(sum(c["kind"] == "negative" for c in quality.CASES), 4)
        for row in quality.CASES:
            added = added_source_lines(row["patch"])
            self.assertTrue(added)
            self.assertEqual([added[n] for n in sorted(added)],
                             row["source"].splitlines())

    def test_precisely_correct_synthetic_responses_pass(self):
        result = quality.evaluate(synthetic_model, fake_parse)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["positives_grounded"], 2)
        self.assertEqual(result["clean_correct"], 4)
        self.assertTrue(result["not_production_accuracy"])

    def test_invented_bug_in_clean_code_fails_closed(self):
        def model(path, patch):
            if path == "fixture/correct_fix.py":
                return json.dumps({"findings": [{
                    "path": path, "line": 2,
                    "code_quote": "return sample_time_ns >= tracking_start_ns",
                    "problem": "Fabricated bug in clean code",
                    "impact": "Cannot be treated as a correct review",
                }]})
            return synthetic_model(path, patch)
        result = quality.evaluate(model, fake_parse)
        self.assertFalse(result["passed"])
        self.assertEqual(result["false_alarms"], 1)

    def test_missing_quote_on_known_bug_fails_closed(self):
        def model(path, patch):
            if path == "fixture/owner.js":
                return json.dumps({"findings": [{
                    "path": path, "line": 2,
                    "problem": "Unknown owner defaults to self",
                    "impact": "Misattributed capture",
                }]})
            return synthetic_model(path, patch)
        result = quality.evaluate(model, fake_parse)
        self.assertFalse(result["passed"])
        self.assertEqual(result["positive_miss_or_ungrounded"], 1)

    def test_unanchored_false_positive_in_clean_code_still_fails(self):
        def model(path, patch):
            if path == "fixture/html.html":
                return json.dumps({"findings": [{
                    "path": path, "line": 12, "code_quote": "imaginary",
                    "problem": "A missing header claimed without any evidence",
                    "impact": "Hypothetical inaccessible page",
                }]})
            return synthetic_model(path, patch)
        result = quality.evaluate(model, fake_parse)
        self.assertFalse(result["passed"])
        self.assertEqual(result["false_alarms"], 1)


if __name__ == "__main__":
    unittest.main()
