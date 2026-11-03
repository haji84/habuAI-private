#!/usr/bin/env python3
"""One approved CPU-only Qwen2.5-Coder 7B comparison; synthetic data only.

The pre-revealed six and frozen forty cases are DIAGNOSTIC, never an unseen
quality certificate. Reuse the exact v1 1.5B reviewer prompts, parser and scorer.
No model-suggested code/input is executed. No real PR source is reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

import cache
import holdout_v1
import measure_holdout
import quality
import review
import synthetic_claims

MODEL = "qwen2.5-coder:7b"
# Published Ollama tag at trial planning: dae161e27b0e...
EXPECTED_MODEL_DIGEST_PREFIX = "dae161e27b0e"
FROZEN_BLOB = "daac52dfed89cb946e736aed49ed109a56307ffa"
FROZEN_SHA256 = "6a679c26f775970a2d55e53e8d3870c6c9cbd8320c530b77725de83af7e8fc8a"
EXPECTED_CODE_BLOBS = {
    "tools/dashboard_ai_review/review.py": "8d65d4b9f37186620d49d9965fde63c9c89606d6",
    "tools/dashboard_ai_review/measure_holdout.py": "49925afa8580b35af59bf65844f76e254edba28d",
    "tools/dashboard_ai_review/quality.py": "a2fd2e24e55133e9d5a15b6975f7454133b67c67",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SYNTHETIC = re.compile(r"^fixture/[A-Za-z0-9_.-]+\.(?:py|js|html)$")
PREFIX = "QWEN7B_COMPARE_"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], timeout=20, text=True).strip()


def require_frozen_source(expected_head: str) -> dict:
    if not isinstance(expected_head, str) or not HEX40.fullmatch(expected_head):
        raise ValueError("INVALID_EXPECTED_HEAD")
    if git("rev-parse", "HEAD") != expected_head:
        raise ValueError("HEAD_MISMATCH")
    if git("hash-object", "tools/dashboard_ai_review/holdout_v1.py") != FROZEN_BLOB:
        raise ValueError("HOLDOUT_BLOB_CHANGED")
    raw = Path("tools/dashboard_ai_review/holdout_v1.py").read_bytes()
    if sha256_bytes(raw) != FROZEN_SHA256:
        raise ValueError("HOLDOUT_BYTES_CHANGED")
    for name, expected in EXPECTED_CODE_BLOBS.items():
        if git("hash-object", name) != expected:
            raise ValueError("REVIEW_SCORER_CHANGED")
    corpus = holdout_v1.instances()
    if (len(corpus) != 40 or
            sum(x["label"] == "positive" for x in corpus) != 20 or
            sum(x["label"] == "negative" for x in corpus) != 20 or
            len(quality.CASES) != 6):
        raise ValueError("FROZEN_CASE_POPULATION_CHANGED")
    return {"head": expected_head, "holdout_blob": FROZEN_BLOB,
            "holdout_sha256": FROZEN_SHA256, "cases": 40,
            "review_source_blobs": EXPECTED_CODE_BLOBS}


def validate_model_digest(digest: str) -> str:
    if (not isinstance(digest, str) or not HEX64.fullmatch(digest)
            or not digest.startswith(EXPECTED_MODEL_DIGEST_PREFIX)):
        raise ValueError("MODEL_DIGEST_NOT_APPROVED")
    return digest


def model_caller(*, max_seconds: int, started_at: float, receipts: list):
    if not isinstance(max_seconds, int) or not 60 <= max_seconds <= 4800:
        raise ValueError("INVALID_CPU_BUDGET")

    def call(path: str, patch: str) -> str:
        # A synthetic review fixture is the ONLY supported input in this trial.
        if (not isinstance(path, str) or not SYNTHETIC.fullmatch(path)
                or not isinstance(patch, str)
                or not patch.startswith("diff --git a/" + path + " b/" + path + "\n")
                or len(patch) > 3500):
            raise ValueError("NON_SYNTHETIC_INPUT_DENIED")
        if time.monotonic() - started_at >= max_seconds:
            raise TimeoutError("APPROVED_CPU_BUDGET_EXHAUSTED")
        receipt = {"ordinal": len(receipts) + 1,
                   "path_sha256": sha256_bytes(path.encode("utf-8")),
                   "patch_sha256": sha256_bytes(patch.encode("utf-8"))}
        try:
            answer = review.ask_model(path, patch, model=MODEL)
            receipt["answer_sha256"] = sha256_bytes(answer.encode("utf-8"))
            receipt["status"] = "COMPLETED"
            return answer
        except (ValueError, OSError, TimeoutError) as error:
            receipt["status"] = "FAILED"
            receipt["error_class"] = type(error).__name__
            raise
        finally:
            # Digests only: no source strings, location, or raw model text.
            receipts.append(receipt)
            print(PREFIX + "RECEIPT: " +
                  json.dumps(receipt, sort_keys=True), flush=True)
    return call


def safe_holdout_summary(result: dict) -> dict:
    fields = ("total", "completed", "incomplete", "known_bug_cases",
              "known_clean_cases", "total_raw_findings",
              "total_location_anchored_findings", "grounding_rejected_findings",
              "parse_dropped_findings", "clean_false_alert_cases",
              "clean_false_alert_rate", "zero_finding_responses",
              "possible_anchored_bug_cases", "proxy_precision_ceiling",
              "proxy_recall_ceiling", "pair_selective_raw_alerts",
              "pair_selective_anchored_proxy", "proxy_gate")
    return {key: result[key] for key in fields}


def run_diagnostic(head: str, max_seconds: int) -> int:
    identity = require_frozen_source(head)
    actual_model = validate_model_digest(cache.model_digest(MODEL))
    print(PREFIX + "IDENTITY: " + json.dumps({
        **identity, "model": MODEL, "model_digest": actual_model,
        "score_status": "DIAGNOSTIC_ONLY", "unseen": False,
        "independent_review": False, "publication_authorized": False
    }, sort_keys=True), flush=True)
    started = time.monotonic()
    receipts = []
    call = model_caller(max_seconds=max_seconds, started_at=started,
                        receipts=receipts)
    smoke = None
    try:
        smoke = quality.evaluate(call, review.parse_findings)
        print(PREFIX + "SIX: " + json.dumps({
            "cases": smoke["cases"], "positives": smoke["positives"],
            "positives_grounded": smoke["positives_grounded"],
            "negatives": smoke["negatives"],
            "clean_correct": smoke["clean_correct"],
            "false_alarms": smoke["false_alarms"],
            "passed": smoke["passed"],
        }, sort_keys=True), flush=True)
    except (ValueError, OSError, TimeoutError) as error:
        print(PREFIX + "SIX_ERROR: " + type(error).__name__, flush=True)
    holdout = None
    try:
        holdout = measure_holdout.score(model_call=call,
                                        parse=review.parse_findings)
        print(PREFIX + "FORTY: " +
              json.dumps(safe_holdout_summary(holdout), sort_keys=True),
              flush=True)
        # The full denominator, including omissions, must always be visible.
        for row in holdout["cases"]:
            record = {"id": row["id"], "label": row["label"],
                      "complete": row["complete"]}
            for key in ("raw_findings", "anchored_findings",
                        "grounding_rejected_findings",
                        "provisional_logic_line_hit", "error"):
                if key in row:
                    record[key] = row[key]
            print(PREFIX + "CASE: " + json.dumps(
                record, sort_keys=True), flush=True)
            for claim in row.get("claim_receipts", []):
                # Bounded, redacted synthetic testimony; NOT a verified bug.
                print(synthetic_claims.log_receipt(claim), flush=True)
    except (ValueError, OSError, TimeoutError, KeyError, TypeError) as error:
        print(PREFIX + "FORTY_ERROR: " + type(error).__name__, flush=True)

    result = {"head": head, "model": MODEL, "model_digest": actual_model,
              "smoke_complete": smoke is not None,
              "smoke_passed": bool(smoke and smoke["passed"]),
              "holdout_complete": bool(holdout and holdout["completed"] == 40),
              "holdout_proxy_gate": holdout["proxy_gate"] if holdout else "INCOMPLETE",
              "model_calls": len(receipts),
              "model_calls_completed": sum(r["status"] == "COMPLETED"
                                           for r in receipts),
              "model_calls_failed": sum(r["status"] == "FAILED"
                                        for r in receipts),
              "elapsed_seconds": round(time.monotonic() - started),
              "unseen_cases": 0, "quality_qualified": False,
              "independent_review_approved": False,
              "release_authorized": False}
    # Missing evaluation is a failure, NOT a safe zero-finding result.
    result["status"] = ("DIAGNOSTIC_MEASURED_QUALITY_HOLD"
                        if smoke is not None and holdout is not None
                        and holdout["completed"] == 40 else "INCOMPLETE_HOLD")
    print(PREFIX + "FINAL: " + json.dumps(result, sort_keys=True),
          flush=True)
    return 0 if result["status"] == "DIAGNOSTIC_MEASURED_QUALITY_HOLD" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--max-seconds", type=int, default=4500)
    arguments = parser.parse_args()
    return run_diagnostic(arguments.expected_head, arguments.max_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
