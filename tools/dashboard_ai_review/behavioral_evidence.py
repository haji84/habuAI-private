"""Evidence-first claim verification: no model-generated code is executed.

The proof engine compares explicit, typed predictions against a trusted witness.
Its current executor is restricted to the *frozen, synthetic* holdout v1. A
future real-code adapter MUST use a separately isolated, authorized test runner
and an independently established expected behavior before calling this API.

A demonstrated return-value discrepancy can confirm a STRUCTURED assertion,
never automatically the free-form problem/impact prose or a PR approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import grounding
import holdout_v1

FROZEN_BLOB = "daac52dfed89cb946e736aed49ed109a56307ffa"
OBSERVATION_SCHEMA = "habu-trusted-behavior-witness-v1"
CLAIM_SCHEMA = "habu-structured-behavior-claim-v1"


def exact_equal(left, right) -> bool:
    """No Python bool == int, mixed list/tuple, or implicit number coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(
            exact_equal(x, y) for x, y in zip(left, right)
        )
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            exact_equal(left[k], right[k]) for k in left
        )
    return left == right


def safe_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frozen_case(case_id: str) -> dict:
    """Validate immutable fixture bytes and resolve only approved case IDs."""
    raw = Path(holdout_v1.__file__).read_bytes()
    actual_blob = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    if actual_blob != FROZEN_BLOB:
        raise ValueError("FROZEN_HOLDOUT_SOURCE_CHANGED")
    if not isinstance(case_id, str) or len(case_id) != 16:
        raise ValueError("INVALID_CASE_ID")
    matches = [x for x in holdout_v1.instances() if x["id"] == case_id]
    if len(matches) != 1:
        raise ValueError("UNKNOWN_FROZEN_CASE")
    return matches[0]


def trusted_synthetic_witness(case_id: str) -> dict:
    """Run a fixed, verified fixture; never execute a model's code or input.

    Run only the exact pinned source and pinned witness arguments. The trusted
    fixture runner is not a sandbox for arbitrary repository source.
    """
    fixture = frozen_case(case_id)
    from test_holdout_v1 import fixture_result
    observed = fixture_result(fixture)
    return {
        "schema": OBSERVATION_SCHEMA,
        "case_id": fixture["id"],
        "source_sha256": sha256_text(fixture["source"]),
        "input": fixture["args"],
        "observed": observed,
        "required": fixture["expected_good"],
        "fixed_fixture_label": fixture["label"],
        "trusted_origin": "pinned_synthetic_holdout_v1",
    }


def compare_behavior(claim: dict, witness: dict, *, citation_ok: bool) -> dict:
    """Reusable pure assertion checker for trusted witness adapters.

    WITNESS TRUST IS A CALLER RESPONSIBILITY: model-provided witness dictionaries
    are untrusted. Only a separately authorized runner may construct them.
    Do not treat this function alone as proof of the runner's identity.
    """
    result = {
        "status": "INCONCLUSIVE",
        "citation_status": "SOURCE_ANCHORED_ONLY" if citation_ok else "CITATION_REJECTED",
        "narrative_semantics": "NOT_AUTOMATICALLY_VERIFIED",
        "source_runtime_provenance": "CALLER_SUPPLIED_TRUSTED_WITNESS",
        "formal_review_approved": False,
        "release_authorized": False,
    }
    if not isinstance(claim, dict) or not isinstance(witness, dict):
        result["status"] = "INVALID_INPUT"
        return result
    if witness.get("schema") != OBSERVATION_SCHEMA:
        result["status"] = "INVALID_WITNESS_SCHEMA"
        return result
    if claim.get("schema") != CLAIM_SCHEMA:
        result["status"] = "UNSTRUCTURED_CLAIM"
        return result
    required = {"case_id", "source_sha256", "input",
                "claimed_actual", "claimed_required"}
    if not required <= claim.keys():
        result["status"] = "MISSING_REPRODUCTION_FIELDS"
        return result
    if (claim["case_id"] != witness.get("case_id")
            or claim["source_sha256"] != witness.get("source_sha256")):
        result["status"] = "SOURCE_OR_CASE_MISMATCH"
        return result
    try:
        for key in ("input", "claimed_actual", "claimed_required"):
            safe_json(claim[key])
        safe_json(witness["input"])
        safe_json(witness["observed"])
        safe_json(witness["required"])
    except (ValueError, TypeError, KeyError):
        result["status"] = "NON_JSON_EVIDENCE"
        return result
    if not exact_equal(claim["input"], witness["input"]):
        result["status"] = "UNTESTED_MODEL_INPUT"
        return result
    if exact_equal(witness["observed"], witness["required"]):
        result["status"] = "NO_DEFECT_ON_TRUSTED_WITNESS"
        return result
    if not exact_equal(claim["claimed_required"], witness["required"]):
        result["status"] = "CLAIMED_REQUIREMENT_CONTRADICTED"
        return result
    if not exact_equal(claim["claimed_actual"], witness["observed"]):
        result["status"] = "CLAIMED_RESULT_CONTRADICTED"
        return result
    # We have reproduced ONLY the declared return value for this one witness.
    # Free-form English/Japanese causal explanations still need adjudication.
    result["status"] = ("REPRODUCED_STRUCTURED_BEHAVIOR"
                        if citation_ok else "REPRODUCED_BEHAVIOR_BAD_CITATION")
    return result


def verify_frozen_synthetic_claim(claim: dict) -> dict:
    """End-to-end adapter for one fixed synthetic case, without arbitrary exec.

    For old unstructured Qwen prose there is no model-asserted exact input and
    actual result, so it must remain UNSTRUCTURED_CLAIM, never auto-certified.
    """
    case_id = claim.get("case_id") if isinstance(claim, dict) else None
    try:
        fixture = frozen_case(case_id)
    except ValueError as exc:
        return {"status": str(exc), "release_authorized": False,
                "formal_review_approved": False}
    if not isinstance(claim, dict):
        return {"status": "INVALID_INPUT", "release_authorized": False,
                "formal_review_approved": False}
    citation_ok = False
    if (isinstance(claim.get("line"), int)
            and not isinstance(claim.get("line"), bool)
            and isinstance(claim.get("code_quote"), str)):
        candidate = {"line": claim["line"],
                     "code_quote": claim["code_quote"],
                     "problem": claim.get("problem", ""),
                     "impact": claim.get("impact", "")}
        located, _ = grounding.ground_candidates(
            [candidate], fixture["source"],
            grounding.added_source_lines(fixture["patch"])
        )
        citation_ok = bool(located)
    # A model-supplied source or input is never executed. Even malformed data
    # must not cause a dynamic model-code invocation.
    if claim.get("schema") != CLAIM_SCHEMA:
        return compare_behavior(claim, {"schema": OBSERVATION_SCHEMA},
                                citation_ok=citation_ok)
    expected_hash = sha256_text(fixture["source"])
    if claim.get("source_sha256") != expected_hash:
        return {"status": "SOURCE_OR_CASE_MISMATCH",
                "citation_status": "SOURCE_ANCHORED_ONLY" if citation_ok else "CITATION_REJECTED",
                "release_authorized": False, "formal_review_approved": False}
    if "input" not in claim or not exact_equal(claim["input"], fixture["args"]):
        return {"status": "UNTESTED_MODEL_INPUT",
                "citation_status": "SOURCE_ANCHORED_ONLY" if citation_ok else "CITATION_REJECTED",
                "release_authorized": False, "formal_review_approved": False}
    try:
        witness = trusted_synthetic_witness(case_id)
    except (OSError, RuntimeError, ValueError, TimeoutError, AssertionError):
        return {"status": "TRUSTED_WITNESS_EXECUTION_FAILED",
                "citation_status": "SOURCE_ANCHORED_ONLY" if citation_ok else "CITATION_REJECTED",
                "release_authorized": False, "formal_review_approved": False}
    return compare_behavior(claim, witness, citation_ok=citation_ok)
