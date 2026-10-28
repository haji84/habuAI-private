#!/usr/bin/env python3
"""Read-only acceptance inspection around the EXISTING Habu P0 / PDCA paths.

This is neither a predictor, issuer, model verifier nor alternate PDCA engine.
In particular a hash, user-supplied start time, JSON flag, and synthetic test
cannot authenticate production authority or scientific source eligibility.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from master_contracts import STAGE_NAMES, validate_night
from pdca_pipeline import (
    _prediction_path, load_predictions, prediction_contract_errors, verify_predictions,
)

JST = ZoneInfo("Asia/Tokyo")


def aware(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    return dt.astimezone(JST)


def night_for(value: datetime) -> str:
    local = value.astimezone(JST)
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()


def inspect(root: Path, night: str, *, actual_start: datetime,
            phase: str, now: datetime | None = None) -> dict:
    """Never write anything. PASS on individual mechanical checks is NOT official E2E PASS."""
    validate_night(night)
    if phase not in ("before", "after"):
        raise ValueError("phase must be before or after")
    if actual_start.tzinfo is None or actual_start.utcoffset() is None:
        raise ValueError("Actual/planned start must be timezone-aware")
    now = now or datetime.now(JST)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Inspection clock must be timezone-aware")
    root = Path(root).absolute()
    start = actual_start.astimezone(JST)
    errors: list[dict] = []
    evidence: dict = {}

    def block(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    if night_for(start) != night:
        block("START_NIGHT_MISMATCH", "Start is outside the requested 07:00 JST operational night")

    if phase == "before":
        # Reuse the authoritative preflight; never create an ORIGINAL or infer a model.
        from check_p0_readiness import inspect as existing_preflight
        pre = existing_preflight(root, night, now=now, planned_start=start)
        evidence["existing_preflight_status"] = pre["status"]
        evidence["existing_p0_directory"] = pre["existing_p0_directory"]
        for problem in pre["blockers"]:
            block(problem["code"], problem["detail"])
    else:
        try:
            predictions = load_predictions(root, night)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            predictions = []
            block("P0_READ_INVALID", f"Canonical ORIGINAL loading failed: {type(exc).__name__}: {exc}")
        p0_rows = [p for p in predictions if p.get("prediction_version") == "P0"]
        if len(p0_rows) != 1:
            block("P0_MISSING_OR_DUPLICATE", f"Expected one canonical ORIGINAL P0; found {len(p0_rows)}")
        else:
            p0 = p0_rows[0]
            problems = prediction_contract_errors(p0, night, "ORIGINAL")
            if problems:
                block("P0_CONTRACT_INVALID", "; ".join(problems))
            integrity, rows = verify_predictions([p0], root=root, night=night)
            evidence["p0_freeze_integrity"] = integrity
            evidence["p0_sidecar"] = rows[0]["sidecar_status"]
            evidence["p0_payload_sha256"] = rows[0].get("expected_sha256")
            if integrity != "PASS":
                block("P0_FREEZE_INVALID", rows[0]["reason"] or integrity)
            try:
                issued = aware(str(p0["created_at"]))
                cutoff = aware(str(p0["cutoff_time"]))
                frozen = aware(str(p0["frozen_at"]))
                evidence["p0_created_at"] = issued.isoformat()
                evidence["p0_frozen_at"] = frozen.isoformat()
                evidence["p0_cutoff_time"] = cutoff.isoformat()
                if not (cutoff <= issued <= frozen < start):
                    block("P0_NOT_PROSPECTIVE", "cutoff <= created <= frozen < actual_start is required")
            except (KeyError, TypeError, ValueError) as exc:
                block("P0_TIME_PROOF_MISSING", f"Invalid issuer chronology: {type(exc).__name__}")
            targets = p0.get("targets_100m_10min")
            if not isinstance(targets, list) or not targets:
                block("FORMAL_TARGETS_NOT_PRODUCED", "No frozen 100m x 10min targets")
            evidence["formal_target_count"] = len(targets) if isinstance(targets, list) else 0
            # The existing hash checker validates immutable bytes, not authority.
            # Never infer a reviewed issuer/Champion from arbitrary JSON assertions.

        report_path = f"reports/pdca/{night}/pdca_result.json"
        try:
            file = _prediction_path(root, report_path)
            if not file.is_file():
                block("PDCA_REPORT_MISSING", "Existing run_pdca parent result not found")
            else:
                report = json.loads(file.read_text(encoding="utf-8"))
                if not isinstance(report, dict) or report.get("operational_night") != night:
                    block("PDCA_REPORT_INVALID", "Report schema/night mismatch")
                else:
                    evidence["pdca_overall_status"] = report.get("overall_status")
                    evidence["pdca_run_id"] = report.get("run_id")
                    stages = report.get("stages")
                    names = [s.get("name") for s in stages if isinstance(s, dict)] if isinstance(stages, list) else []
                    if len(names) != len(STAGE_NAMES) or set(names) != set(STAGE_NAMES):
                        block("PDCA_STAGES_INCOMPLETE", "Canonical nine parent stages absent or duplicated")
                    elif any(s.get("status") != "PASS" for s in stages):
                        block("PDCA_SCIENTIFIC_GATES_OPEN", "One or more required canonical stages are not PASS")
                    if report.get("overall_status") != "PASS" or report.get("completed") is not True:
                        block("PDCA_NOT_COMPLETED", "Parent has not certified an all-stage successful run")
                    run_id = report.get("run_id")
                    if not isinstance(run_id, str) or not re.fullmatch("[0-9a-f]{64}", run_id):
                        block("PDCA_RUN_ID_INVALID", "Missing source-bound master run identifier")
                    else:
                        stored = _prediction_path(root, f"reports/pdca/{night}/runs/{run_id}/run_manifest.json")
                        if not stored.is_file() or stored.read_bytes() != file.read_bytes():
                            block("PDCA_MANIFEST_NOT_BOUND", "Compatibility pointer differs from immutable run manifest")
                    operational = report.get("operational_result")
                    p0_score = operational.get("p0_score") if isinstance(operational, dict) else None
                    if not isinstance(p0_score, dict) or p0_score.get("strict_official_score_eligible") is not True:
                        block("OFFICIAL_SCORE_NOT_CERTIFIED", "An authenticated official P0 score is unavailable")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            block("PDCA_REPORT_INVALID", f"Cannot validate canonical parent report: {type(exc).__name__}: {exc}")

    # Key safety boundary: a locally inspectable file cannot attest actual
    # trusted source/original issuance or independent production authorization.
    block("TRUSTED_REAL_E2E_UNATTESTED",
          "Trusted issuance, real source/completeness, independent review and GitHub-run provenance "
          "must be verified by the authorized production coordinator, not this local checker")

    return {
        "schema_version": "habu-next-real-night-e2e-inspection-v1",
        "phase": phase,
        "operational_night": night,
        "actual_or_planned_start": start.isoformat(),
        "checked_at": now.astimezone(JST).isoformat(),
        "status": "BLOCKED",
        "official_e2e_complete": False,
        "read_only": True,
        "evidence": evidence,
        "blockers": errors,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--night", required=True)
    p.add_argument("--actual-start", required=True, help="JST start with +09:00 offset")
    p.add_argument("--phase", choices=("before", "after"), required=True)
    args = p.parse_args()
    try:
        result = inspect(args.root, args.night, actual_start=aware(args.actual_start), phase=args.phase)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
