"""Read-only semantic audit of actual Qwen synthetic claim text and fixed witnesses.

This tests the integrity of a human-authored claim-level interpretation.
A witness reproducing a violation is not by itself evidence the model explained
it correctly. The saved textual adjudication remains a separate, explicit
interpretive step, not an automatic approval/precision certification.

No real user data, GPS, external inference, model output execution, network,
code-generation workflow or GitHub write privileges.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

import holdout_v1
from test_holdout_v1 import fixture_result

REPO = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = REPO / "docs/qa/synthetic/qwen_claims_run_41369985317.json"
ADJUDICATION_PATH = REPO / "docs/qa/synthetic/qwen_claim_adjudications_run_41369985317.json"
FROZEN_HOLDOUT_GIT_BLOB = "daac52dfed89cb946e736aed49ed109a56307ffa"
FROZEN_CLAIM_SNAPSHOT_BLOB = "41ae317a71342132323bae080b0635d119950cca"
FROZEN_SEMANTIC_ADJUDICATION_BLOB = "4e3c7a0dfcca6366c85935ab9f237290c99cc80c"


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


VERDICTS = {
    "BEHAVIOR_REPRODUCED_BY_WITNESS",
    "CLAIM_CONTRADICTED_BY_BEHAVIOR",
    "CLAIM_MIXED_OR_UNSUPPORTED",
}


def _data():
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    audit = json.loads(ADJUDICATION_PATH.read_text(encoding="utf-8"))
    instances = holdout_v1.instances()
    return snapshot, audit, instances


class OriginalModelClaimAuditTests(unittest.TestCase):
    def test_original_model_text_and_human_interpretation_are_byte_frozen(self):
        self.assertEqual(git_blob_sha(SNAPSHOT_PATH), FROZEN_CLAIM_SNAPSHOT_BLOB)
        self.assertEqual(git_blob_sha(ADJUDICATION_PATH),
                         FROZEN_SEMANTIC_ADJUDICATION_BLOB)

    def test_exactly_forty_real_model_claims_are_accounted_for(self):
        snapshot, audit, instances = _data()
        self.assertEqual(snapshot["source_run"], 41369985317)
        self.assertEqual(snapshot["source_job"], 125038398498)
        self.assertEqual(snapshot["source_head"],
                         "30c5315174d6da2931a0be7fe9fa05e3222f90c4")
        self.assertEqual(snapshot["holdout_git_blob"], FROZEN_HOLDOUT_GIT_BLOB)
        self.assertEqual(audit["source_holdout_git_blob"], FROZEN_HOLDOUT_GIT_BLOB)
        self.assertTrue(audit["labels_unchanged"])
        self.assertEqual(len(snapshot["claims"]), 40)
        self.assertEqual(len(audit["adjudications"]), 40)
        self.assertEqual(
            [x["case_id"] for x in snapshot["claims"]],
            [x["id"] for x in instances],
        )
        self.assertEqual(
            [x["case_id"] for x in audit["adjudications"]],
            [x["id"] for x in instances],
        )
        self.assertEqual(
            [x["claim_id"] for x in snapshot["claims"]],
            [x["claim_id"] for x in audit["adjudications"]],
        )
        self.assertEqual(len({x["claim_id"] for x in snapshot["claims"]}), 40)

    def test_source_anchor_and_claim_semantics_remain_independent(self):
        snapshot, audit, instances = _data()
        counts = {v: 0 for v in VERDICTS}
        for receipt, interpretation, item in zip(
                snapshot["claims"], audit["adjudications"], instances):
            self.assertIn(interpretation["verdict"], VERDICTS)
            counts[interpretation["verdict"]] += 1
            self.assertEqual(interpretation["model_anchor_status"],
                             receipt["source_anchor"])
            self.assertEqual(interpretation["family"], item["family"])
            self.assertEqual(
                interpretation["expected_class"],
                "bug_variant" if item["label"] == "positive" else "clean_variant",
            )
            self.assertTrue(interpretation["reason"].strip())
            self.assertEqual(interpretation["witness_args"], item["args"])
            self.assertEqual(
                interpretation["expected_correct_output"],
                item["expected_good"],
            )
            self.assertNotIn("REVIEW_APPROVED", interpretation["verdict"])
            # Model's source citation can be incorrect even when its
            # broader description of the known violation is correct.
            self.assertIn(receipt["source_anchor"],
                          ("SOURCE_ANCHORED_ONLY", "CITATION_REJECTED",
                           "MODEL_FINDING_REJECTED_BY_PARSER"))
        self.assertEqual(counts["BEHAVIOR_REPRODUCED_BY_WITNESS"], 16)
        self.assertEqual(counts["CLAIM_CONTRADICTED_BY_BEHAVIOR"], 20)
        self.assertEqual(counts["CLAIM_MIXED_OR_UNSUPPORTED"], 4)

    def test_frozen_behavior_witness_is_reexecuted_for_every_adjudication(self):
        snapshot, audit, instances = _data()
        # Every pair has the same documented input. Run ONLY trusted, immutable
        # fixtures; model-supplied code is NEVER executed here.
        for item, a in zip(instances, audit["adjudications"]):
            with self.subTest(id=item["id"]):
                observed = fixture_result(item)
                expected = a["expected_correct_output"]
                if item["label"] == "positive":
                    self.assertNotEqual(observed, expected)
                    self.assertNotEqual(
                        type(observed), type(None),
                        "A missing oracle result must not be treated as a bug",
                    )
                else:
                    self.assertEqual(observed, expected)
                    self.assertIs(type(observed), type(expected))
                # Witness labels never override the model's claim verdict.
                if a["verdict"] == "CLAIM_CONTRADICTED_BY_BEHAVIOR":
                    self.assertEqual(item["label"], "negative")
                elif a["verdict"] == "CLAIM_MIXED_OR_UNSUPPORTED":
                    self.assertEqual(item["label"], "positive")

    def test_text_archive_is_bounded_synthetic_and_no_approval(self):
        snapshot, audit, instances = _data()
        self.assertIn("synthetic", snapshot["fact"].lower())
        self.assertIn("not an independent second model", audit["scope"].lower())
        for row in snapshot["claims"]:
            self.assertLessEqual(len(row["model_problem"]), 225)
            self.assertLessEqual(len(row["model_impact"]), 205)
            self.assertLessEqual(len(row["model_code_quote"]), 165)
            self.assertNotIn("BEGIN PRIVATE KEY", json.dumps(row))
        self.assertEqual(
            sum(x["source_anchor"] == "SOURCE_ANCHORED_ONLY"
                for x in snapshot["claims"]),
            9,
        )
        self.assertFalse(any("APPROVED" in a["verdict"]
                             for a in audit["adjudications"]))


if __name__ == "__main__":
    unittest.main()
