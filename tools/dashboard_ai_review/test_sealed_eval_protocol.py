"""Protocol-only tests for a genuinely sealed synthetic reviewer evaluation.

The 40 examples here are local TEST DOUBLES, not a fresh model benchmark.
No model call, GPS, personal capture data, or production approval occurs.
"""
import copy
import json
import unittest

import sealed_eval_protocol as p

# Fake test keys are deliberately PUBLIC and must NEVER be considered
# independent-custodian credentials in a real evaluation.
OWNER_KEY = b"test-only-implementation-owner-key-000000001"
CUSTODIAN_KEY = b"test-only-external-custodian-key-000000002"
COLLECTOR_KEY = b"test-only-prediction-collector-key-00000003"
REVIEWER_KEY = b"test-only-separate-reviewer-key-0000000004"


def sample_cases():
    items = []
    for n in range(40):
        cid = f"{n+1000:016x}"
        language = "python" if n < 20 else "js"
        suffix = "py" if language == "python" else "js"
        name = f"fixture/sealed_{cid}.{suffix}"
        # Intentionally trivial MODEL-FREE test doubles: not an evaluation.
        src = ("def check(x):\n    return x + 1\n" if n < 20
               else "function check(x) { return x + 1; }\n")
        patch = (f"diff --git a/{name} b/{name}\n"
                 f"new file mode 100644\n--- /dev/null\n+++ b/{name}\n"
                 f"@@ -0,0 +1,{len(src.splitlines())} @@\n" +
                 "".join("+" + line + "\n" for line in src.splitlines()))
        casespec = {
            "case_id": cid, "language": language, "path": name,
            "source": src, "patch": patch,
            "source_sha256": p.sha(src),
            "label": "BUG" if n % 2 == 0 else "CLEAN",
            "critical": n in (0, 20),
            "test_input": [3],
            "observed": 4,
            "required": 5 if n % 2 == 0 else 4,
            "runner_id": "synthetic-test-runner",
        }
        casespec["witness_sha256"] = p.sha({
            "case_id": cid, "source_sha256": casespec["source_sha256"],
            "input": casespec["test_input"], "observed": casespec["observed"],
            "required": casespec["required"], "runner_id": casespec["runner_id"],
        })
        items.append(casespec)
    return items


def prepare(scheme="selective"):
    freeze = p.sign({
        "stage": "freeze", "schema": p.SCHEMA,
        "implementation_owner": "implementer-A",
        "git_head": "a" * 40, "model_name": "qwen2.5-coder:7b",
        "model_digest": "b" * 64,
        "reviewer_sha256": "c" * 64,
        "prompt_sha256": "d" * 64,
        "scorer_sha256": "e" * 64,
        "executor_sha256": "f" * 64,
        "thresholds": dict(p.THRESHOLDS),
    }, OWNER_KEY)
    cohort = p.seal_cohort(freeze, sample_cases(), "independent-custodian-B",
                           CUSTODIAN_KEY)
    public_bundle = p.seal_public_cases(cohort, CUSTODIAN_KEY)
    public = p.public_projection(public_bundle)
    model = []
    for original in cohort["payload"]["cases"]:
        cid = original["case_id"]
        label = original["label"]
        should_alert = (scheme == "all" or
                        scheme == "selective" and label == "BUG")
        findings = ([{"line": 2 if original["language"] == "python" else 1,
                      "code_quote": "return x + 1",
                      "problem": "Test-only explicit witness claim",
                      "impact": "Test-only observed discrepancy"}]
                    if should_alert else [])
        response = {"case_id": cid, "source_sha256": original["source_sha256"],
                    "findings": findings}
        response["response_sha256"] = p.sha(
            {k: v for k, v in response.items() if k != "response_sha256"})
        model.append(response)
    predictions = p.seal_predictions(freeze, public_bundle, public, model,
                                     "prediction-collector-C", COLLECTOR_KEY)
    adjudications = []
    for response in model:
        for ordinal, _finding in enumerate(response["findings"], 1):
            case = next(item for item in cohort["payload"]["cases"]
                        if item["case_id"] == response["case_id"])
            adjudications.append({
                "case_id": case["case_id"], "ordinal": ordinal,
                "response_sha256": response["response_sha256"],
                "witness_sha256": case["witness_sha256"],
                "verdict": "REPRODUCED" if case["label"] == "BUG"
                           else "REFUTED",
            })
    review = p.seal_adjudications(predictions, adjudications,
                                  "independent-reviewer-D", REVIEWER_KEY)
    return freeze, cohort, public_bundle, predictions, review


def evaluate(bundle):
    return p.score(*bundle, owner_key=OWNER_KEY, custodian_key=CUSTODIAN_KEY,
                   collector_key=COLLECTOR_KEY, reviewer_key=REVIEWER_KEY)


class SealedGateTests(unittest.TestCase):
    def test_model_visible_projection_excludes_all_answers_and_witnesses(self):
        _freeze, cohort, public_bundle, _, _ = prepare()
        public = p.public_projection(public_bundle)
        self.assertEqual(len(public), 40)
        for case in public:
            self.assertEqual(set(case), {"case_id", "path", "patch", "source_sha256"})
            for forbidden in ("label", "observed", "required", "witness_sha256",
                              "critical", "test_input", "runner_id"):
                self.assertNotIn(forbidden, case)

    def test_selective_toy_screening_does_not_issue_fake_quality_qualification(self):
        result = evaluate(prepare())
        self.assertEqual(result["issued_findings"], 20)
        self.assertEqual(result["confirmed_true_findings"], 20)
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["clean_false_alert_rate"], 0.0)
        self.assertEqual(result["critical_misses"], 0)
        self.assertTrue(result["metric_screen_pass"])
        self.assertEqual(result["decision"], "INDEPENDENT_REVIEW_BLOCKED")
        self.assertFalse(result["quality_qualified"])

    def test_all_warning_model_fails_without_changing_denominators(self):
        result = evaluate(prepare("all"))
        self.assertEqual((result["issued_findings"], result["confirmed_true_findings"]),
                         (40, 20))
        self.assertEqual(result["precision"], .5)
        self.assertEqual(result["recall"], 1)
        self.assertEqual(result["clean_false_alert_rate"], 1)
        self.assertFalse(result["metric_screen_pass"])

    def test_all_silent_model_has_zero_recall_not_a_pass(self):
        result = evaluate(prepare("none"))
        self.assertEqual(result["issued_findings"], 0)
        self.assertEqual(result["precision"], 0)
        self.assertEqual(result["recall"], 0)
        self.assertEqual(result["critical_misses"], 2)
        self.assertFalse(result["metric_screen_pass"])

    def test_missing_or_duplicate_prediction_cannot_become_clean_case(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        for corrupt in ("missing", "duplicate"):
            with self.subTest(corrupt=corrupt):
                modified = copy.deepcopy(pred)
                if corrupt == "missing":
                    modified["payload"]["responses"].pop()
                else:
                    modified["payload"]["responses"][0] = modified["payload"]["responses"][1]
                modified["signature"] = p.signature(
                    modified["payload"], COLLECTOR_KEY)
                with self.assertRaisesRegex(ValueError, "PREDICTION_POPULATION"):
                    evaluate((freeze, cohort, public_bundle, modified, review))

    def test_tampering_with_label_after_seal_is_rejected(self):
        bundle = list(prepare())
        modified = copy.deepcopy(bundle[1])
        modified["payload"]["cases"][0]["label"] = "CLEAN"
        bundle[1] = modified
        with self.assertRaisesRegex(ValueError, "BAD_SIGNATURE"):
            evaluate(bundle)

    def test_tampered_prediction_cannot_pass_even_if_scores_look_better(self):
        bundle = list(prepare("all"))
        modified = copy.deepcopy(bundle[3])
        modified["payload"]["responses"][1]["findings"] = []
        bundle[3] = modified
        with self.assertRaisesRegex(ValueError, "BAD_SIGNATURE"):
            evaluate(bundle)

    def test_old_prediction_commit_replay_fails_after_freeze_changes(self):
        bundle = list(prepare())
        new_freeze = copy.deepcopy(bundle[0])
        new_freeze["payload"]["git_head"] = "0" * 40
        new_freeze["signature"] = p.signature(new_freeze["payload"], OWNER_KEY)
        bundle[0] = new_freeze
        with self.assertRaisesRegex(ValueError, "FREEZE_BINDING"):
            evaluate(bundle)

    def test_duplicate_cases_and_old_revealed_names_rejected_before_model(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        cases = sample_cases()
        cases[-1]["case_id"] = cases[0]["case_id"]
        with self.assertRaises(ValueError):
            p.seal_cohort(freeze, cases, "independent-custodian-B", CUSTODIAN_KEY)
        cases = sample_cases()
        cases[0]["path"] = "fixture/holdout_861163c0458e3dbd.py"
        with self.assertRaises(ValueError):
            p.seal_cohort(freeze, cases, "independent-custodian-B", CUSTODIAN_KEY)

    def test_nonindependent_named_actor_is_rejected(self):
        freeze, _, _, _, _ = prepare()
        with self.assertRaisesRegex(ValueError, "ROLE_SEPARATION"):
            p.seal_cohort(freeze, sample_cases(), "implementer-A", CUSTODIAN_KEY)

    def test_adjudication_may_not_claim_unissued_finding(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        changed = copy.deepcopy(review)
        changed["payload"]["adjudications"].append(
            dict(changed["payload"]["adjudications"][0], ordinal=3))
        changed["signature"] = p.signature(changed["payload"], REVIEWER_KEY)
        with self.assertRaisesRegex(ValueError, "ADJUDICATION_POPULATION"):
            evaluate((freeze, cohort, public_bundle, pred, changed))

    def test_broken_signed_reviewer_witness_is_rejected(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        altered = copy.deepcopy(review)
        altered["payload"]["adjudications"][0]["witness_sha256"] = "0" * 64
        altered["signature"] = p.signature(altered["payload"], REVIEWER_KEY)
        with self.assertRaisesRegex(ValueError, "WITNESS"):
            evaluate((freeze, cohort, public_bundle, pred, altered))

    def test_normal_case_cannot_be_marked_as_true_positive(self):
        freeze, cohort, public_bundle, pred, review = prepare("all")
        modified = copy.deepcopy(review)
        clean_id = next(c["case_id"] for c in cohort["payload"]["cases"]
                        if c["label"] == "CLEAN")
        item = next(a for a in modified["payload"]["adjudications"]
                    if a["case_id"] == clean_id)
        item["verdict"] = "REPRODUCED"
        modified["signature"] = p.signature(modified["payload"], REVIEWER_KEY)
        with self.assertRaisesRegex(ValueError, "CLEAN"):
            evaluate((freeze, cohort, public_bundle, pred, modified))

    def test_forged_critical_flag_rejected_by_signature(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        altered = copy.deepcopy(cohort)
        altered["payload"]["cases"][0]["critical"] = False
        with self.assertRaisesRegex(ValueError, "BAD_SIGNATURE"):
            evaluate((freeze, altered, public_bundle, pred, review))

    def test_model_claim_not_allowed_to_set_own_label(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        modified = copy.deepcopy(pred)
        modified["payload"]["responses"][0]["label"] = "BUG"
        modified["signature"] = p.signature(modified["payload"], COLLECTOR_KEY)
        with self.assertRaisesRegex(ValueError, "MODEL_RESPONSE_SCHEMA"):
            evaluate((freeze, cohort, public_bundle, modified, review))

    def test_separate_collector_does_not_receive_private_labels_or_inputs(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        public_data = public_bundle["payload"]
        self.assertEqual(public_data["stage"], "public")
        self.assertEqual(set(public_data), {
            "stage", "schema", "cohort_sha256", "freeze_sha256",
            "custodian_id", "public_cases",
        })
        exported = json.dumps(public_data, ensure_ascii=False)
        for forbidden in ('"label":', '"observed":', '"required":',
                          '"critical":', '"test_input":', '"runner_id":',
                          '"witness_sha256":'):
            self.assertNotIn(forbidden, exported)
        self.assertEqual(len(public_data["public_cases"]), 40)

    def test_private_cohort_cannot_be_used_as_collector_input(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        responses = copy.deepcopy(pred["payload"]["responses"])
        with self.assertRaisesRegex(ValueError, "PUBLIC_CASES_REQUIRED"):
            p.seal_predictions(freeze, cohort, p.public_projection(public_bundle),
                               responses, "prediction-collector-C", COLLECTOR_KEY)

    def test_signed_public_packet_must_match_private_cohort_at_reveal(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        forged = copy.deepcopy(public_bundle)
        forged["payload"]["public_cases"][0]["source_sha256"] = "0" * 64
        forged["signature"] = p.signature(forged["payload"], CUSTODIAN_KEY)
        with self.assertRaisesRegex(ValueError, "COHORT_BINDING"):
            evaluate((freeze, cohort, forged, pred, review))

    def test_tampered_public_case_packet_is_rejected(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        forged = copy.deepcopy(public_bundle)
        forged["payload"]["public_cases"][0]["path"] = "fixture/private.py"
        with self.assertRaisesRegex(ValueError, "BAD_SIGNATURE"):
            evaluate((freeze, cohort, forged, pred, review))

    def test_nan_and_duplicate_json_keys_are_invalid(self):
        for raw in ('{"v":NaN}', '{"v":1,"v":2}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                p.parse_json(raw)

    def test_patch_must_match_the_exact_signed_source_bytes(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        cases = sample_cases()
        cases[0]["patch"] = cases[0]["patch"].replace(
            "return x + 1", "return x + 100", 1)
        # A matching path and source SHA are NOT sufficient when the model
        # actually sees a different implementation in the diff.
        with self.assertRaisesRegex(ValueError, "SYNTHETIC_SOURCE_CHANGED"):
            p.seal_cohort(freeze, cases, "independent-custodian-B", CUSTODIAN_KEY)

    def test_threshold_boolean_cannot_masquerade_as_zero_misses(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        forged = copy.deepcopy(freeze)
        forged["payload"]["thresholds"]["critical_misses_max"] = False
        forged["signature"] = p.signature(forged["payload"], OWNER_KEY)
        with self.assertRaisesRegex(ValueError, "INVALID_FREEZE"):
            evaluate((forged, cohort, public_bundle, pred, review))

    def test_critical_flag_cannot_be_placed_on_clean_cases(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        cases = sample_cases()
        cases[1]["critical"] = True
        with self.assertRaisesRegex(ValueError, "INVALID_CRITICAL"):
            p.seal_cohort(freeze, cases, "independent-custodian-B", CUSTODIAN_KEY)

    def test_wrong_model_citation_cannot_be_certified_as_reproduced(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        changed = copy.deepcopy(pred)
        target = next(x for x in changed["payload"]["responses"]
                      if x["findings"])
        target["findings"][0]["line"] = 999
        target["response_sha256"] = p.sha({
            k: v for k, v in target.items() if k != "response_sha256"
        })
        changed["signature"] = p.signature(changed["payload"], COLLECTOR_KEY)
        adjusted = copy.deepcopy(review)
        adjusted["payload"]["predictions_sha256"] = p.sha(changed["payload"])
        for a in adjusted["payload"]["adjudications"]:
            if a["case_id"] == target["case_id"]:
                a["response_sha256"] = target["response_sha256"]
        adjusted["signature"] = p.signature(adjusted["payload"], REVIEWER_KEY)
        with self.assertRaisesRegex(ValueError, "UNANCHORED"):
            evaluate((freeze, cohort, public_bundle, changed, adjusted))

    def test_typed_boolean_is_not_silently_equal_to_integer(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        mutated = copy.deepcopy(cohort)
        mutated["payload"]["cases"][0]["observed"] = True
        mutated["payload"]["cases"][0]["required"] = 1
        mutated["payload"]["cases"][0]["witness_sha256"] = p.sha({
            "case_id": mutated["payload"]["cases"][0]["case_id"],
            "source_sha256": mutated["payload"]["cases"][0]["source_sha256"],
            "input": mutated["payload"]["cases"][0]["test_input"],
            "observed": True, "required": 1,
            "runner_id": mutated["payload"]["cases"][0]["runner_id"],
        })
        mutated["signature"] = p.signature(mutated["payload"], CUSTODIAN_KEY)
        # Model predictions now refer to a different sealed case pack.
        with self.assertRaisesRegex(ValueError, "COHORT_BINDING"):
            evaluate((freeze, mutated, public_bundle, pred, review))

    def test_self_certifying_without_separate_reviewer_key_fails(self):
        freeze, cohort, public_bundle, pred, review = prepare()
        with self.assertRaisesRegex(ValueError, "ROLE_KEYS"):
            p.score(freeze, cohort, public_bundle, pred, review,
                    owner_key=OWNER_KEY, custodian_key=OWNER_KEY,
                    collector_key=COLLECTOR_KEY, reviewer_key=REVIEWER_KEY)


if __name__ == "__main__":
    unittest.main()
