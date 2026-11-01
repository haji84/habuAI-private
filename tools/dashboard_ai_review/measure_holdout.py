#!/usr/bin/env python3
"""Synthetic 40-case Qwen holdout; all model calls use local Ollama only.

The model sees a frozen path + patch. The label and behavior witness never
enter the inference request. Source-line grounding is NOT semantic validation.
Metrics are explicitly proxy upper bounds, not formal precision/recall or
GitHub approval. No owner locations, GPS logs or source datasets are touched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import grounding
import holdout_v1
import review

COUNT = 40
BUG_CASES = 20
CLEAN_CASES = 20


def logic_line(source: str) -> int:
    candidates = [
        idx for idx, line in enumerate(source.splitlines(), 1)
        if "return " in line and not line.lstrip().startswith(("#", "//"))
    ]
    if len(candidates) != 1:
        raise ValueError("Each frozen case needs one actual return line")
    return candidates[0]


def score(model_call=None, parse=None) -> dict:
    if model_call is None:
        model_call = review.ask_model
    if parse is None:
        parse = review.parse_findings
    cases = holdout_v1.instances()
    if (len(cases) != COUNT
            or sum(c["label"] == "positive" for c in cases) != BUG_CASES
            or sum(c["label"] == "negative" for c in cases) != CLEAN_CASES):
        raise ValueError("Frozen cohort missing 20 bug + 20 clean cases")
    records = []
    for item in cases:
        target = holdout_v1.public_prompt_instance(item)
        if set(target) != {"path", "patch"}:
            raise ValueError("Holdout labels leaked into model inputs")
        try:
            raw_text = model_call(target["path"], target["patch"])
            decoded = json.loads(raw_text)
            if (not isinstance(decoded, dict)
                    or not isinstance(decoded.get("findings"), list)
                    or len(decoded["findings"]) > review.MAX_FINDINGS_PER_FILE):
                raise ValueError("Invalid model response schema")
            raw = len(decoded["findings"])
            parsed = parse(raw_text, item["path"])
            anchored, counts = grounding.ground_candidates(
                parsed, item["source"], grounding.added_source_lines(item["patch"])
            )
            if sum(counts.values()) != len(parsed):
                raise ValueError("Grounding inventory mismatch")
            parsed_dropped = raw - len(parsed)
            grounding_rejected = sum(
                n for reason, n in counts.items()
                if reason != "LOCATION_ANCHORED_NOT_BUG_VERIFIED"
            )
            if (parsed_dropped < 0 or
                    raw != parsed_dropped + grounding_rejected + len(anchored)):
                raise ValueError("Raw / parsed / grounded candidate accounting mismatch")
            found_logic = item["label"] == "positive" and any(
                claim["line"] == logic_line(item["source"]) for claim in anchored
            )
            records.append({
                "id": item["id"], "label": item["label"],
                "language": item["language"], "complete": True,
                "raw_findings": raw, "parsed_findings": len(parsed),
                "anchored_findings": len(anchored),
                "parse_dropped_findings": parsed_dropped,
                "grounding_rejected_findings": grounding_rejected,
                "grounding_rejection_reasons": {
                    reason: n for reason, n in counts.items()
                    if reason != "LOCATION_ANCHORED_NOT_BUG_VERIFIED"
                },
                "provisional_logic_line_hit": bool(found_logic),
                "unanchored_count": raw - len(anchored),
            })
        except (ValueError, TypeError, KeyError, OSError, TimeoutError) as error:
            records.append({
                "id": item["id"], "label": item["label"],
                "language": item["language"], "complete": False,
                "error": type(error).__name__,
            })
    bugs = [r for r in records if r["label"] == "positive"]
    clean = [r for r in records if r["label"] == "negative"]
    done = [r for r in records if r["complete"]]
    incomplete = COUNT - len(done)
    possible_tp = sum(r["provisional_logic_line_hit"] for r in bugs if r["complete"])
    clean_pass = sum(r["raw_findings"] == 0 for r in clean if r["complete"])
    false_alert_cases = sum(r["raw_findings"] > 0 for r in clean if r["complete"])
    false_alerts = sum(r["raw_findings"] for r in clean if r["complete"])
    raw_zero = sum(r["raw_findings"] == 0 for r in done)
    ungrounded = sum(r["unanchored_count"] for r in done)
    parse_dropped = sum(r["parse_dropped_findings"] for r in done)
    grounding_rejected = sum(r["grounding_rejected_findings"] for r in done)
    anchored_total = sum(r["anchored_findings"] for r in done)
    raw_total = sum(r["raw_findings"] for r in done)
    anchored_positive_cases = sum(
        r["anchored_findings"] > 0 for r in bugs if r["complete"]
    )
    anchored_clean_false_alert_cases = sum(
        r["anchored_findings"] > 0 for r in clean if r["complete"]
    )
    anchored_clean_false_alert_findings = sum(
        r["anchored_findings"] for r in clean if r["complete"]
    )
    if raw_total != anchored_total + parse_dropped + grounding_rejected:
        raise ValueError("Aggregate model finding accounting mismatch")
    # Precision and recall denominators MUST refer to explicit, coherent
    # populations. Previous denominator mixed accepted positive citations
    # with rejected/raw alerts on clean files; it was NOT a precision ceiling.
    # This is a ceiling for location-anchored findings ONLY, and even
    # citations on the expected return line are not semantically verified.
    proxy_precision = possible_tp / anchored_total if anchored_total else 0.0
    proxy_recall = possible_tp / BUG_CASES
    false_alert_rate = false_alert_cases / CLEAN_CASES
    provisional = (incomplete == 0 and possible_tp >= 16
                   and proxy_precision >= .95 and false_alert_rate <= .05)
    return {
        "schema": "habu-reviewer-holdout-v1", "total": COUNT,
        "completed": len(done), "incomplete": incomplete,
        "known_bug_cases": len(bugs), "known_clean_cases": len(clean),
        "possible_anchored_bug_cases": possible_tp,
        "clean_unflagged_cases": clean_pass,
        "clean_false_alert_cases": false_alert_cases,
        "clean_false_alert_findings": false_alerts,
        "anchored_clean_false_alert_cases": anchored_clean_false_alert_cases,
        "anchored_clean_false_alert_findings": anchored_clean_false_alert_findings,
        "anchored_clean_false_alert_rate": round(
            anchored_clean_false_alert_cases / CLEAN_CASES, 4
        ),
        "anchored_positive_candidate_cases": anchored_positive_cases,
        "total_raw_findings": raw_total,
        "total_location_anchored_findings": anchored_total,
        "parse_dropped_findings": parse_dropped,
        "grounding_rejected_findings": grounding_rejected,
        "unanchored_findings": ungrounded,
        "zero_finding_responses": raw_zero,
        "proxy_precision_ceiling": round(proxy_precision, 4),
        "proxy_precision_population": "location_anchored_findings_only",
        "proxy_recall_ceiling": round(proxy_recall, 4),
        "clean_false_alert_rate": round(false_alert_rate, 4),
        "proxy_gate": ("INCOMPLETE" if incomplete else
                       "PROVISIONAL" if provisional else "HOLD"),
        "formal_semantic_validation": "NOT_DONE",
        "production_quality": "NOT_EVALUATED",
        "official_github_approval": False,
        "cases": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-holdout-blob", required=True)
    args = parser.parse_args()
    if not (len(args.expected_head) == 40
            and all(c in "0123456789abcdef" for c in args.expected_head)):
        raise ValueError("Invalid immutable PR HEAD")
    if review.git("rev-parse", "HEAD") != args.expected_head:
        raise ValueError("Checkout differs from frozen target HEAD")
    relative = "tools/dashboard_ai_review/holdout_v1.py"
    expected = args.expected_holdout_blob
    actual = review.git("hash-object", relative)
    if actual != expected:
        raise ValueError("Frozen holdout Git blob identity changed")
    holdout_sha256 = hashlib.sha256(Path(holdout_v1.__file__).read_bytes()).hexdigest()
    model_digest = review.reviewer_cache.model_digest(review.MODEL)
    print("HOLDOUT_MODEL: " + review.MODEL + " digest=" + model_digest, flush=True)
    print("HOLDOUT_CORPUS_BLOB: " + actual + " SHA256=" + holdout_sha256, flush=True)
    print("HOLDOUT_HEAD: " + args.expected_head, flush=True)
    result = score()
    for row in result["cases"]:
        print("HOLDOUT_CASE: id={} label={} complete={} raw={} grounded={} logic_hit={} error={}".format(
            row["id"], row["label"], row["complete"],
            row.get("raw_findings", "NA"), row.get("anchored_findings", "NA"),
            row.get("provisional_logic_line_hit", False),
            row.get("error", "none")), flush=True)
        if row["complete"]:
            print("HOLDOUT_ANCHOR_DIAG: id={} parsed={} parse_dropped={} rejected={} reasons={}".format(
                row["id"], row["parsed_findings"], row["parse_dropped_findings"],
                row["grounding_rejected_findings"],
                json.dumps(row["grounding_rejection_reasons"], sort_keys=True),
            ), flush=True)
    totals = {k: v for k, v in result.items() if k != "cases"}
    print("HOLDOUT_TOTALS: " + json.dumps(totals, sort_keys=True), flush=True)
    text = "\n".join([
        "## 40-case local CPU reviewer quality holdout (advisory only)",
        "",
        "PR HEAD: " + args.expected_head,
        "Model digest: " + model_digest,
        "Frozen holdout SHA256: " + holdout_sha256,
        "",
        "~~~json", json.dumps(totals, sort_keys=True, indent=2), "~~~",
        "",
        "A valid source quote proves a LOCATION ONLY. Precision ceiling here "
        "uses LOCATION-ANCHORED findings as its denominator; raw clean alerts "
        "are reported separately. Neither metric establishes actual bug correctness.",
        "No location originals, no external model API, no GitHub approval.",
    ]) + "\n"
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
    return 0 if result["proxy_gate"] == "PROVISIONAL" else 2


if __name__ == "__main__":
    sys.exit(main())
