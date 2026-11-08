"""Reproduce nine documented Qwen7B *diagnostic* failures with pinned fixtures.

No arbitrary model code, source, or model-selected input is ever executed.
This auditor does NOT repair model answers or certify their free-form prose.
It separates raw model alerts, source anchors, independently fixed witnesses,
and formal (unavailable) sealed/independent quality certification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import behavioral_evidence as be
import grounding
import holdout_v1

FROZEN_BLOB = "daac52dfed89cb946e736aed49ed109a56307ffa"
FROZEN_SHA256 = "6a679c26f775970a2d55e53e8d3870c6c9cbd8320c530b77725de83af7e8fc8a"
LEDGER_GIT_BLOB = "823222fc16bb397708d7cf0a91658aaadb9dd842"
MODEL_RUN = 41414177747
MODEL_HEAD = "46f55a69a32f39ebb9c6e7b11426fcb3064bab21"
MODEL_DIGEST = "dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364"
LEDGER = (Path(__file__).resolve().parents[2] /
          "docs/qa/synthetic/qwen7b_failure_nine_run_41414177747.json")
HEX64 = re.compile(r"^[a-f0-9]{64}$")


def load_ledger(path: Path = LEDGER) -> dict:
    """Byte-preserving JSON evidence inventory. Not a model response parser."""
    raw = path.read_bytes()
    actual_blob = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    if actual_blob != LEDGER_GIT_BLOB:
        raise ValueError("ORIGINAL_QWEN7B_LEDGER_TAMPERED")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or set(data) != {
        "schema", "source", "note", "cases"
    }:
        raise ValueError("INVALID_NINE_CASE_LEDGER")
    return data


def audit_revealed_failures(data: dict, *, runner=None) -> dict:
    """Use the original *fixed* fixture executor and type-exact checks.

    The supplied witness runner is injectible for tests; callers must NOT
    substitute an untrusted executable. No release permission is returned.
    """
    if runner is None:
        from test_holdout_v1 import fixture_result as runner
    # Confirm original frozen source bytes BEFORE invoking the fixture runner.
    frozen = be.frozen_case
    rows = data.get("cases") if isinstance(data, dict) else None
    source = data.get("source") if isinstance(data, dict) else None
    if (data.get("schema") != "habu-qwen7b-nine-diagnostic-witnesses-v1"
            or not isinstance(source, dict)
            or source.get("run_id") != MODEL_RUN
            or source.get("job_id") != 125173894377
            or source.get("head") != MODEL_HEAD
            or source.get("model_digest") != MODEL_DIGEST
            or source.get("frozen_holdout_blob") != FROZEN_BLOB
            or source.get("frozen_holdout_sha256") != FROZEN_SHA256
            or source.get("known_diagnostic_only") is not True
            or source.get("independent_review") is not False
            or not isinstance(rows, list) or len(rows) != 9):
        raise ValueError("UNAUTHORIZED_OR_INCOMPLETE_DIAGNOSTIC")
    # Git object identity is verified by frozen_case for each member.
    expected_ids = {
        "3ac311996fe9795e", "ac388422ed977b73", "c7be0a54b75e44da",
        "62d12de11961f5d9", "2bf126048752fa72", "aa48572f6eed538e",
        "f9b3c4fbd57552ed", "568dc5a6463ad176", "386d0b6b0f1f290d",
    }
    if {r.get("case_id") for r in rows if isinstance(r, dict)} != expected_ids:
        raise ValueError("CASE_POPULATION_CHANGED")
    if len({r["case_id"] for r in rows}) != len(rows):
        raise ValueError("DUPLICATED_CASE")

    inventory = holdout_v1.instances()
    results = []
    for row in rows:
        item = frozen(row["case_id"])
        ordinal = next((i + 7 for i, x in enumerate(inventory)
                        if x["id"] == row["case_id"]), None)
        if (item["family"] != row.get("family")
                or item["language"] != row.get("language")
                or item["label"] != row.get("case_label")
                or row.get("source_requirement") not in item["source"]
                or row.get("source_code") not in item["source"]
                or not be.exact_equal(item["args"], row.get("case_input"))
                or not be.exact_equal(item["expected_good"],
                                      row.get("required_return"))
                or row.get("model_call_ordinal") != ordinal):
            raise ValueError("FROZEN_CASE_OR_WITNESS_TAMPERED")
        if any(not isinstance(row.get(k), str) or not HEX64.fullmatch(row[k])
               for k in ("model_response_sha256", "model_patch_sha256",
                         "model_path_sha256")):
            raise ValueError("INVALID_MODEL_RECEIPT")
        if (be.sha256_text(item["patch"]) != row["model_patch_sha256"]
                or be.sha256_text(item["path"]) != row["model_path_sha256"]):
            raise ValueError("MODEL_PATCH_OR_PATH_MISMATCH")
        raw_count = row.get("model_raw_findings")
        anchors = row.get("model_location_anchors")
        claims = row.get("model_claims")
        if (type(raw_count) is not int or raw_count not in (0, 1)
                or type(anchors) is not int or not 0 <= anchors <= raw_count
                or not isinstance(claims, list) or len(claims) != raw_count):
            raise ValueError("MODEL_FINDING_ACCOUNTING_CHANGED")
        # Source line matching does NOT verify the model's allegation.
        for claim in claims:
            candidate = {
                "line": claim.get("model_line"),
                "code_quote": claim.get("code_quote"),
                "problem": claim.get("problem"),
                "impact": claim.get("impact"),
            }
            anchored, _ = grounding.ground_candidates(
                [candidate], item["source"],
                grounding.added_source_lines(item["patch"]))
            if not anchored or anchors != len(claims):
                raise ValueError("MODEL_SOURCE_CITATION_UNVERIFIED")

        # The only executed code comes from the known pinned fixture, and the
        # test harness chooses the input, never an LLM-generated payload.
        actual = runner(item)
        if not be.exact_equal(actual, row.get("observed_return")):
            raise ValueError("WITNESS_OBSERVATION_DID_NOT_REPRODUCE")
        has_defect_on_witness = not be.exact_equal(actual, item["expected_good"])
        if row["case_label"] == "negative" and not has_defect_on_witness:
            classification = "FALSE_ALERT_ON_FIXED_WITNESS" if raw_count else "CLEAN_NO_ALERT"
        elif row["case_label"] == "positive" and has_defect_on_witness:
            classification = "MISSED_FIXED_WITNESS" if raw_count == 0 else "UNVERIFIED_CANDIDATE"
        else:
            raise ValueError("FROZEN_LABEL_CONTRADICTED_BY_EXECUTION")
        if ((row["category"] == "FALSE_ALERT") !=
                (classification == "FALSE_ALERT_ON_FIXED_WITNESS")
                or (row["category"] == "MISSING_RAW_ALERT") !=
                (classification == "MISSED_FIXED_WITNESS")):
            raise ValueError("CATEGORY_MISREPRESENTED")
        results.append({
            "case_id": row["case_id"],
            "family": row["family"],
            "classification": classification,
            "witness_input": item["args"],
            "observed": actual,
            "required": item["expected_good"],
            "raw_model_alerts": raw_count,
            "source_citation_only": anchors,
            "model_response_sha256": row["model_response_sha256"],
            "prose_independently_verified": False,
        })
    false_alarms = sum(x["classification"] == "FALSE_ALERT_ON_FIXED_WITNESS"
                       for x in results)
    misses = sum(x["classification"] == "MISSED_FIXED_WITNESS"
                 for x in results)
    if (false_alarms, misses) != (3, 6):
        raise ValueError("NINE_CASE_CAUSE_INVENTORY_CHANGED")
    return {
        "schema": "habu-qwen7b-nine-executed-witness-audit-v1",
        "run_id": MODEL_RUN, "head": MODEL_HEAD, "model_digest": MODEL_DIGEST,
        "executed_fixed_witnesses": len(results),
        "false_alert_cases_on_fixed_witnesses": false_alarms,
        "missed_fixed_defects": misses,
        "model_prose_semantically_approved": 0,
        "reproduced_7b_issued_structured_claims": 0,
        "unseen_cases": 0,
        "quality_qualified": False,
        "independent_review_approved": False,
        "release_authorized": False,
        "decision": "QUALITY_HOLD",
        "cases": results,
    }


def main() -> int:
    result = audit_revealed_failures(load_ledger())
    for item in result["cases"]:
        print("QWEN7B_NINE_CASE: " + json.dumps(
            item, sort_keys=True, ensure_ascii=True), flush=True)
    totals = {k: v for k, v in result.items() if k != "cases"}
    print("QWEN7B_NINE_TOTALS: " +
          json.dumps(totals, sort_keys=True, ensure_ascii=True), flush=True)
    return 0  # Executable witness accounting passed, NOT model quality.


if __name__ == "__main__":
    raise SystemExit(main())
