"""Six source-grounded semantic adjudications of real Qwen synthetic claims.

Every model claim below originated in the 2026-11-02 GitHub CPU review:
run 41354115659, job 124990438170, frozen fixture set quality.CASES.

Statuses describe each *model claim*, not the code base and not the 40-case
holdout. Do not use these known answers to tune prompts or report a model PASS.
"""
from __future__ import annotations

from html.parser import HTMLParser
import subprocess
import shutil
import unittest

import quality

SOURCE_RUN = 41354115659
SOURCE_JOB = 124990438170

CLAIMS = (
    {
        "fixture": "stale_prestart_defect",
        "model_claim": "should_record accepts fixes measured before tracking began",
        "status": "REPRODUCED_CLAIM_WITH_INVALID_MODEL_CITATION",
        "evidence": "With tracking_start_ns=100, sample_time_ns=95, the function returns True instead of False.",
    },
    {
        "fixture": "unknown_owner_defaults_to_self",
        "model_claim": "When item.owner is null or undefined, normalizeOwner throws TypeError",
        "status": "CONTRADICTED_BY_EXECUTION",
        "evidence": "normalizeOwner({owner:null}) returns 'self'; the underlying misattribution is real but the alleged exception is not.",
    },
    {
        "fixture": "correct_prestart_guard",
        "model_claim": "should_record fails to test sample_time_ns >= tracking_start_ns",
        "status": "CONTRADICTED_BY_EXECUTION",
        "evidence": "With sample_time_ns=95 and tracking_start_ns=100, the guarded function returns False.",
    },
    {
        "fixture": "correct_owner_validation",
        "model_claim": "normalizeOwner does not validate that owner is self or other",
        "status": "CONTRADICTED_BY_EXECUTION",
        "evidence": "The code rejects 'unknown' and accepts both self and other.",
    },
    {
        "fixture": "defined_callback_not_missing",
        "model_claim": "gpsStart fails to validate its position before returning",
        "status": "INSUFFICIENT_REQUIREMENT_FOR_DEFECT",
        "evidence": "The fixture specifies a callback wiring check, not geolocation validation. The callback exists and works.",
    },
    {
        "fixture": "complete_labeled_html",
        "model_claim": "The HTML header has no closing tag",
        "status": "CONTRADICTED_BY_SOURCE",
        "evidence": "The fragment contains an explicit </header> and a labelled button.",
    },
)

class HeaderProbe(HTMLParser):
    def __init__(self):
        super().__init__()
        self.opened = 0
        self.closed = 0
        self.labels = []
    def handle_starttag(self, tag, attrs):
        if tag == "header": self.opened += 1
        if tag == "button": self.labels.append(dict(attrs).get("aria-label"))
    def handle_endtag(self, tag):
        if tag == "header": self.closed += 1


class ClaimAdjudicationTests(unittest.TestCase):
    def test_exactly_six_original_claims_are_classified_without_mutation(self):
        self.assertEqual(len(CLAIMS), 6)
        self.assertEqual({x["fixture"] for x in CLAIMS},
                         {x["name"] for x in quality.CASES})
        statuses = [x["status"] for x in CLAIMS]
        self.assertEqual(statuses.count("REPRODUCED_CLAIM_WITH_INVALID_MODEL_CITATION"), 1)
        self.assertEqual(sum(s.startswith("CONTRADICTED") for s in statuses), 4)
        self.assertEqual(statuses.count("INSUFFICIENT_REQUIREMENT_FOR_DEFECT"), 1)

    def test_gps_claim_reproduced_but_evidence_citation_is_separate(self):
        original = next(x["source"] for x in quality.CASES
                        if x["name"] == "stale_prestart_defect")
        scope = {}
        exec(compile(original, "<trusted-frozen-quality-fixture>", "exec"), scope)
        self.assertIs(scope["should_record"](95, 100), True)
        self.assertIs(scope["should_record"](100, 100), True)

    def test_correct_prestart_claim_contradicted(self):
        original = next(x["source"] for x in quality.CASES
                        if x["name"] == "correct_prestart_guard")
        scope = {}
        exec(compile(original, "<trusted-frozen-quality-fixture>", "exec"), scope)
        self.assertIs(scope["should_record"](95, 100), False)
        self.assertIs(scope["should_record"](100, 100), True)

    def run_fixed_js(self, key, assertions):
        if not shutil.which("node"):
            self.skipTest("Node.js required")
        src = next(x["source"] for x in quality.CASES if x["name"] == key)
        proc = subprocess.run(["node", "-e", src + "\n" + assertions],
                              capture_output=True, text=True, timeout=12)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unknown_owner_exception_claim_is_contradicted(self):
        self.run_fixed_js(
            "unknown_owner_defaults_to_self",
            "const assert=require('node:assert/strict');"
            "assert.equal(normalizeOwner({owner:null}),'self');"
            "assert.equal(normalizeOwner({owner:undefined}),'self');"
        )

    def test_correct_owner_validation_claim_is_contradicted(self):
        self.run_fixed_js(
            "correct_owner_validation",
            "const assert=require('node:assert/strict');"
            "assert.throws(()=>normalizeOwner({owner:'unknown'}),/Invalid owner/);"
            "assert.equal(normalizeOwner({owner:'self'}),'self');"
            "assert.equal(normalizeOwner({owner:'other'}),'other');"
        )

    def test_callback_is_defined_but_extra_requirements_not_inferred(self):
        self.run_fixed_js(
            "defined_callback_not_missing",
            "const assert=require('node:assert/strict');"
            "assert.equal(gpsStart({watchPosition(fn){return fn(42)}}),42);"
        )

    def test_html_closing_tag_claim_is_contradicted(self):
        src = next(x["source"] for x in quality.CASES
                   if x["name"] == "complete_labeled_html")
        parser = HeaderProbe()
        parser.feed(src)
        self.assertEqual(parser.opened, parser.closed)
        self.assertEqual(parser.opened, 1)
        self.assertEqual(parser.labels, ["Save"])

if __name__ == "__main__":
    unittest.main()
