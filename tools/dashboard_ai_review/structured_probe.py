"""Synthetic-only model-emitted counterexample bridge.

Uses the immutable *revealed* 40-case development corpus only.
No model-generated code or selected inputs are ever executed.
No human/GitHub/security review or unseen-performance approval.
"""
import argparse
import json
import re
import subprocess

import behavioral_evidence as be
import holdout_v1
import review
import synthetic_claims

FIELDS = {"case_id", "source_sha256", "path", "line", "code_quote",
          "problem", "impact", "input_json", "actual_json", "required_json"}
WITNESSED = {"REPRODUCED_STRUCTURED_BEHAVIOR",
             "REPRODUCED_BEHAVIOR_BAD_CITATION",
             "NO_DEFECT_ON_TRUSTED_WITNESS",
             "CLAIMED_REQUIREMENT_CONTRADICTED", "CLAIMED_RESULT_CONTRADICTED"}


def _pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def _bad_constant(_value):
    raise ValueError("NONFINITE_JSON")


def _json(value):
    if not isinstance(value, str) or not 0 < len(value) <= 400:
        raise ValueError("UNBOUNDED_JSON_FIELD")
    return json.loads(value, object_pairs_hook=_pairs, parse_constant=_bad_constant)


def _model_claim(row, item):
    if not isinstance(row, dict) or set(row) != FIELDS:
        raise ValueError("MISSING_OR_ADDED_MODEL_FIELD")
    for name in ("case_id", "source_sha256", "path", "code_quote", "problem", "impact"):
        if not isinstance(row[name], str):
            raise ValueError("WRONG_MODEL_TEXT_TYPE")
    if (len(row["case_id"]) != 16 or len(row["source_sha256"]) != 64
            or row["path"] != item["path"] or type(row["line"]) is not int
            or not 1 <= row["line"] <= 100000
            or not 0 < len(row["code_quote"]) <= 160
            or not 12 <= len(row["problem"]) <= 220
            or not 8 <= len(row["impact"]) <= 200):
        raise ValueError("MALFORMED_MODEL_CLAIM")
    return {"schema": be.CLAIM_SCHEMA, "case_id": row["case_id"],
            "source_sha256": row["source_sha256"],
            "line": row["line"], "code_quote": row["code_quote"],
            "problem": row["problem"], "impact": row["impact"],
            "input": _json(row["input_json"]),
            "claimed_actual": _json(row["actual_json"]),
            "claimed_required": _json(row["required_json"])}


def _invalid(count=None):
    return {"status": "INVALID_MODEL_RESPONSE", "raw_findings": count,
            "claims": [], "release_authorized": False, "quality_qualified": False}


def assess_model_output(item, raw):
    """Use only model-emitted typed assertions and a fixed independent witness.

    The evidence digest identifies bytes/results, not an independent reviewer's
    identity, provenance of arbitrary PR source, or authorization to publish.
    """
    count = None
    try:
        fixed = be.frozen_case(item["id"])
        if (fixed["source"] != item["source"]
                or fixed["path"] != item["path"]
                or fixed["args"] != item["args"]):
            raise ValueError("UNTRUSTED_CASE")
        if not isinstance(raw, str) or not 0 < len(raw) <= 16384:
            return _invalid()
        obj = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_bad_constant)
        if (not isinstance(obj, dict) or set(obj) != {"findings"}
                or not isinstance(obj["findings"], list)
                or len(obj["findings"]) > 3):
            return _invalid()
        count = len(obj["findings"])
        if count == 0:
            return {"status": "NO_MODEL_CLAIMS", "raw_findings": 0,
                    "claims": [], "release_authorized": False, "quality_qualified": False}
        assertions = [_model_claim(row, fixed) for row in obj["findings"]]
    except (ValueError, TypeError, KeyError, AttributeError, IndexError):
        return _invalid(count)

    claims = []
    for assertion in assertions:
        if (assertion["case_id"] != fixed["id"]
                or assertion["source_sha256"] != be.sha256_text(fixed["source"])):
            # Never dispatch an unknown model-controlled identity to the runner.
            verdict = {"status": "SOURCE_OR_CASE_MISMATCH",
                       "citation_status": "CITATION_REJECTED"}
        else:
            verdict = be.verify_frozen_synthetic_claim(assertion)
        evidence_sha = None
        if verdict["status"] in WITNESSED:
            try:
                # This is the second execution of the same fixed fixture, NEVER
                # the Qwen-proposed input. Do not use model-supplied trust flags.
                witnessed = be.trusted_synthetic_witness(fixed["id"])
                evidence_sha = be.sha256_text(be.safe_json({
                    "schema": "fixed-synthetic-reproduction-v1",
                    "source_sha256": be.sha256_text(fixed["source"]),
                    "witness": witnessed}))
            except (ValueError, OSError, RuntimeError, TimeoutError, AssertionError):
                verdict["status"] = "TRUSTED_WITNESS_EXECUTION_FAILED"
        claims.append({"status": verdict["status"],
                       "citation_status": verdict.get("citation_status", "CITATION_REJECTED"),
                       "evidence_sha256": evidence_sha, "narrative_verified": False,
                       "formal_review_approved": False})
    return {"status": "ADVISORY_ONLY", "raw_findings": count, "claims": claims,
            "release_authorized": False, "quality_qualified": False}


def _sample():
    population = holdout_v1.instances()
    return [next(item for item in population
                 if item["language"] == language and item["label"] == label)
            for language, label in (("python", "positive"), ("python", "negative"),
                                    ("js", "positive"), ("js", "negative"))]


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("--expected-head", required=True)
    head = arg.parse_args().expected_head
    if not re.fullmatch(r"[a-f0-9]{40}", head):
        raise ValueError("MISSING_EXACT_HEAD")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=15).strip()
    if actual != head:
        raise ValueError("HEAD_CHANGED")
    digest = review.reviewer_cache.model_digest(review.MODEL)
    print("STRUCTURED_MODEL_ID: {} digest={} head={}".format(
        review.MODEL, digest, head), flush=True)
    completed = 0
    clean_raw_alarms = 0
    structured_hits = 0
    for item in _sample():
        result = {"id": item["id"], "language": item["language"],
                  "label": item["label"], "source_sha256": be.sha256_text(item["source"])}
        try:
            raw = review.ask_model(item["path"], item["patch"], evidence_case=(
                item["id"], be.sha256_text(item["source"])))
            verdict = assess_model_output(item, raw)
            result["model_reply_sha256"] = be.sha256_text(raw)
            # Bounded synthetic-only text, stripped of control/secret-shaped tokens.
            result["model_reply_excerpt"] = synthetic_claims.safe_synthetic_text(raw, 1800)
            result["status"] = verdict["status"]
            result["raw_findings"] = verdict["raw_findings"]
            result["evidence"] = verdict["claims"]
            if verdict["status"] in ("NO_MODEL_CLAIMS", "ADVISORY_ONLY"):
                completed += 1
                clean_raw_alarms += bool(item["label"] == "negative" and verdict["raw_findings"])
                structured_hits += sum(x["status"] == "REPRODUCED_STRUCTURED_BEHAVIOR"
                                       for x in verdict["claims"])
        except (ValueError, OSError, TimeoutError, RuntimeError) as exc:
            result["status"] = "MODEL_CALL_FAILED"
            result["error_class"] = type(exc).__name__
        print("STRUCTURED_PROBE_CASE: " + json.dumps(
            result, sort_keys=True, ensure_ascii=True), flush=True)
    print("STRUCTURED_PROBE_TOTALS: " + json.dumps({
        "cases": 4, "complete": completed, "clean_raw_alerts": clean_raw_alarms,
        "reproduced_structured_witnesses": structured_hits, "unseen_cases": 0,
        "formal_review_approved": False, "quality_qualified": False,
        "state": "DIAGNOSTIC_ONLY" if completed == 4 else "INCOMPLETE_HOLD",
    }, sort_keys=True), flush=True)
    return 0 if completed == 4 else 2


if __name__ == "__main__":
    raise SystemExit(main())
