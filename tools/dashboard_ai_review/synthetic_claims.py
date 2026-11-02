"""Evidence receipts for claims about the fixed synthetic 40-case holdout.

This file NEVER imports, reads or prints real PR source, owner data, GPS or GPX.
All model-visible strings come only from holdout_v1 synthetic fixtures.
An exact source citation never proves a model claim is correct.
"""
from __future__ import annotations

import hashlib
import json
import re

from grounding import ground_candidates, added_source_lines

MAX_CLAIMS_PER_CASE = 3
LIMITS = {"problem": 220, "impact": 200, "code_quote": 160}
REDACT = re.compile(
    r"(?:ghp_[A-Za-z0-9]{18,}|github_pat_[A-Za-z0-9_]{18,}|"
    r"sk-proj-[A-Za-z0-9_-]{14,}|-----BEGIN [\w ]+PRIVATE KEY-----)"
)


def safe_synthetic_text(value: object, max_chars: int) -> str:
    """Bound and encode untrusted model prose for GitHub Actions console."""
    if not isinstance(value, str):
        return ""
    result = "".join(
        " " if (ord(char) < 32 or ord(char) == 127) else char
        for char in value
    )
    result = REDACT.sub("[REDACTED]", result)
    return result[:max_chars]


def claim_receipts(item: dict, response: dict, parsed: list[dict]) -> list[dict]:
    """Attach source evidence and conservative semantic status to each claim.

    Verify each individual raw candidate rather than inferring verification
    from a file-level count. Labels/witnesses do not enter any model call.
    """
    if (not isinstance(item, dict)
            or not re.fullmatch(r"fixture/holdout_[0-9a-f]{16}\.(?:py|js)",
                                item.get("path", ""))
            or item.get("label") not in ("positive", "negative")
            or not isinstance(item.get("source"), str)
            or not isinstance(item.get("patch"), str)
            or not isinstance(response, dict)
            or not isinstance(response.get("findings"), list)):
        raise ValueError("Only frozen synthetic holdout cases may produce claim receipts")
    if len(response["findings"]) > MAX_CLAIMS_PER_CASE:
        raise ValueError("Unbounded model findings")
    added = added_source_lines(item["patch"])
    found = []
    for ordinal, row in enumerate(response["findings"], 1):
        if not isinstance(row, dict):
            row = {}
        marker = str(item["id"]) + ":" + str(ordinal)
        claim_id = hashlib.sha256(marker.encode("ascii")).hexdigest()[:16]
        # The supplied raw claim may have been truncated by the source parser.
        # Compare bounded fields separately before applying strict grounding.
        candidates = [candidate for candidate in parsed if (
            candidate.get("path") == row.get("path")
            and candidate.get("line") == row.get("line")
            and candidate.get("problem") ==
                str(row.get("problem", "")).strip()[:220]
            and candidate.get("code_quote") ==
                str(row.get("code_quote", "")).strip()[:160]
        )]
        if candidates:
            grounded, counts = ground_candidates([candidates[0]], item["source"], added)
            if grounded:
                anchor_status = "SOURCE_ANCHORED_ONLY"
                anchor_reason = "LOCATION_ANCHORED_NOT_BUG_VERIFIED"
            else:
                anchor_status = "CITATION_REJECTED"
                anchor_reason = next(iter(counts))
        else:
            anchor_status = "MODEL_FINDING_REJECTED_BY_PARSER"
            anchor_reason = "SCHEMA_OR_TEXT_NOT_ACCEPTED"
        found.append({
            "case_id": item["id"],
            "claim_id": claim_id,
            "ordinal": ordinal,
            "anchor_status": anchor_status,
            "anchor_reason": anchor_reason,
            "semantic_status": "UNVERIFIED_REQUIRES_CLAIM_SPECIFIC_COUNTEREXAMPLE",
            "fixture_witness": (
                "FIXTURE_VIOLATES_STATED_RULE"
                if item["label"] == "positive"
                else "FIXTURE_PASSES_FIXED_WITNESS"
            ),
            "model_line": row.get("line") if isinstance(row.get("line"), int)
                           and not isinstance(row.get("line"), bool) else None,
            "model_problem": safe_synthetic_text(row.get("problem", ""), LIMITS["problem"]),
            "model_impact": safe_synthetic_text(row.get("impact", ""), LIMITS["impact"]),
            "model_code_quote": safe_synthetic_text(
                row.get("code_quote", ""), LIMITS["code_quote"]
            ),
        })
    return found


def log_receipt(receipt: dict) -> str:
    """All console output is a one-line ASCII-escaped JSON record."""
    return "HOLDOUT_CLAIM_TEXT: " + json.dumps(
        receipt, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
