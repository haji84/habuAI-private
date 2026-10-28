#!/usr/bin/env python3
"""Read-only acceptance inspection around the EXISTING Habu P0 / PDCA paths.

This is neither a predictor, issuer, model verifier nor alternate PDCA engine.
In particular a hash, user-supplied start time, JSON flag, and synthetic test
cannot authenticate production authority or scientific source eligibility.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from master_contracts import STAGE_NAMES, canonical_bytes, validate_night
from pdca_pipeline import (
    _prediction_path, prediction_contract_errors, verify_predictions,
)

JST = ZoneInfo("Asia/Tokyo")
MAX_JSON_BYTES = 16 * 1024**2
MAX_TOTAL_BYTES = 64 * 1024**2
MAX_READS = 128
MAX_ENTRIES = 256
MAX_VERSIONS = 64
MAX_DEPTH = 32
MAX_NODES = 200_000
MAX_TOTAL_NODES = 500_000
CHUNK_BYTES = 64 * 1024
MAX_SECONDS = 30


class _Limit(ValueError):
    """A resource blocker, never a partial successful inspection."""


class _Budget:
    def __init__(self):
        self.deadline = time.monotonic() + MAX_SECONDS
        self.bytes = self.reads = self.nodes = 0

    def check(self):
        if time.monotonic() >= self.deadline:
            raise _Limit("RUNTIME_BLOCKED: observer deadline expired")

    def read(self, root, relative, limit=MAX_JSON_BYTES):
        self.check()
        self.reads += 1
        if self.reads > MAX_READS:
            raise _Limit("CAPACITY_BLOCKED: observer artifact capture/reopen count")
        if self.bytes > MAX_TOTAL_BYTES:
            raise _Limit("CAPACITY_BLOCKED: observer cumulative actual bytes")
        path = _prediction_path(root, relative)
        if not path.is_file():
            raise OSError("Observer artifact is not a regular file")
        captured = bytearray()
        with path.open("rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise OSError("Observer artifact is not a regular file")
            while True:
                self.check()
                remaining = min(limit - len(captured), MAX_TOTAL_BYTES - self.bytes)
                block = stream.read(min(CHUNK_BYTES, remaining + 1))
                self.bytes += len(block)  # The overflow sentinel is charged too.
                if len(captured) + len(block) > limit or self.bytes > MAX_TOTAL_BYTES:
                    raise _Limit("CAPACITY_BLOCKED: observer artifact/cumulative actual bytes")
                if not block:
                    break
                captured.extend(block)
        self.check()
        return bytes(captured)


def _json(raw, budget):
    """Bound lexical nesting/tokens before the existing JSON decoder allocates."""
    depth = nodes = 0
    quoted = escaped = scalar = False
    for index, byte in enumerate(raw):
        if index % 4096 == 0:
            budget.check()
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
            continue
        node = False
        if byte == 34:
            quoted, scalar, node = True, False, True
        elif byte in (91, 123):
            depth += 1
            scalar, node = False, True
            if depth > MAX_DEPTH:
                raise _Limit("CAPACITY_BLOCKED: observer JSON depth")
        elif byte in (93, 125):
            depth -= 1
            scalar = False
        elif byte in (9, 10, 13, 32, 44, 58):
            scalar = False
        elif not scalar:
            scalar, node = True, True
        if node:
            nodes += 1  # Includes object keys and overwritten duplicate tokens.
            budget.nodes += 1
            if nodes > MAX_NODES or budget.nodes > MAX_TOTAL_NODES:
                raise _Limit("CAPACITY_BLOCKED: observer JSON node count")
    budget.check()
    value = json.loads(raw.decode("utf-8"))
    budget.check()
    pending, visited = [value], 0
    while pending:
        budget.check()
        item = pending.pop()
        visited += 1
        if visited > MAX_NODES:
            raise _Limit("CAPACITY_BLOCKED: observer parsed JSON node count")
        if isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return value


def _load_originals(root, night, budget):
    base = _prediction_path(root, f"predictions/original/{night}")
    if not base.exists():
        return []
    directories = []
    with os.scandir(base) as entries:
        for count, entry in enumerate(entries, 1):
            budget.check()
            if count > MAX_ENTRIES:
                raise _Limit("CAPACITY_BLOCKED: observer directory entry count")
            if entry.name.startswith("P"):
                relative = f"predictions/original/{night}/{entry.name}"
                checked = _prediction_path(root, relative)
                if checked.is_dir():
                    directories.append(checked)
                    if len(directories) > MAX_VERSIONS:
                        raise _Limit("CAPACITY_BLOCKED: observer P-directory count")
    directories.sort(key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 10**9)
    predictions = []
    for directory in directories:
        relative = (directory / "prediction.json").relative_to(root).as_posix()
        if not _prediction_path(root, relative).exists():
            continue
        payload = _json(budget.read(root, relative), budget)
        if not isinstance(payload, dict):
            raise ValueError("Malformed ORIGINAL prediction object")
        payload["_path"] = str(Path(relative))
        payload["_directory_version"] = directory.name
        predictions.append(payload)
    return predictions


def _verify_captured_p0(p0, root, night, budget):
    # Keep the existing pure hash contract; its root facade has uncapped reopens.
    budget.check()
    _, rows = verify_predictions([p0], root=None, night=night)
    budget.check()
    row = rows[0]
    version, stored = p0.get("_directory_version"), p0.get("_path")
    relative = (f"predictions/original/{night}/{version}/prediction.json"
                if isinstance(version, str) and re.fullmatch(r"P(0|[1-9][0-9]*)", version)
                else None)
    if (relative is not None and isinstance(stored, str) and
            stored.replace("\\", "/") == relative and p0.get("prediction_class") == "ORIGINAL"):
        expected = p0.get("payload_sha256")
        try:
            side_relative = f"predictions/original/{night}/{version}/sha256.txt"
            sidecar = _prediction_path(root, side_relative)
            _prediction_path(root, relative)
            if not sidecar.exists():
                row["sidecar_status"] = "MISSING"
                if row["status"] == "PASS":
                    row.update(status="PARTIAL", reason="Immutable Freeze sidecar missing")
            elif not sidecar.is_file() or sidecar.stat().st_size > 130:
                row.update(sidecar_status="INVALID", status="FAIL", reason="Invalid Freeze sidecar file")
            elif budget.read(root, side_relative, 130) != (str(expected) + "  prediction.json\n").encode("ascii"):
                row.update(sidecar_status="MISMATCH", status="FAIL", reason="Immutable Freeze sidecar mismatch")
            else:
                row["sidecar_status"] = "MATCH"
                record = {k: v for k, v in p0.items() if not k.startswith("_")}
                budget.check()
                canonical = canonical_bytes(record) + b"\n"
                budget.check()
                if budget.read(root, relative) != canonical:
                    row.update(sidecar_status="NONCANONICAL_BYTES", status="FAIL",
                               reason="Immutable prediction.json bytes changed")
        except _Limit as exc:
            row.update(sidecar_status="INVALID", status="FAIL", reason=str(exc))
        except (OSError, ValueError, UnicodeError) as exc:
            row.update(sidecar_status="INVALID", status="FAIL",
                       reason=f"Freeze sidecar verification failed: {type(exc).__name__}")
    budget.check()
    return row["status"], rows


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
    budget = _Budget()

    def block(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    if night_for(start) != night:
        block("START_NIGHT_MISMATCH", "Start is outside the requested 07:00 JST operational night")

    if phase == "before":
        # Reuse the authoritative preflight; never create an ORIGINAL or infer a model.
        try:
            budget.check()
            from check_p0_readiness import inspect as existing_preflight
            pre = existing_preflight(root, night, now=now, planned_start=start)
            budget.check()
            evidence["existing_preflight_status"] = pre["status"]
            evidence["existing_p0_directory"] = pre["existing_p0_directory"]
            for problem in pre["blockers"]:
                block(problem["code"], problem["detail"])
        except ModuleNotFoundError as exc:
            if exc.name != "fcntl":
                raise
            block("P0_PREFLIGHT_RUNTIME_BLOCKED",
                  "RUNTIME_BLOCKED: canonical preflight requires unavailable fcntl; "
                  "no preflight or production-authority result was produced")
        except (OSError, ValueError) as exc:
            block("P0_READ_INVALID", f"Canonical preflight failed: {type(exc).__name__}: {exc}")
    else:
        try:
            predictions = _load_originals(root, night, budget)
        except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            predictions = []
            block("P0_READ_INVALID", f"Canonical ORIGINAL loading failed: {type(exc).__name__}: {exc}")
        if not all(isinstance(p, dict) for p in predictions):
            block("P0_READ_INVALID", "Malformed ORIGINAL prediction object")
            predictions = []
        p0_rows = [p for p in predictions if p.get("prediction_version") == "P0"]
        if len(p0_rows) != 1:
            block("P0_MISSING_OR_DUPLICATE", f"Expected one canonical ORIGINAL P0; found {len(p0_rows)}")
        else:
            p0 = p0_rows[0]
            problems = prediction_contract_errors(p0, night, "ORIGINAL")
            if problems:
                block("P0_CONTRACT_INVALID", "; ".join(problems))
            try:
                integrity, rows = _verify_captured_p0(p0, root, night, budget)
                evidence["p0_freeze_integrity"] = integrity
                evidence["p0_sidecar"] = rows[0]["sidecar_status"]
                evidence["p0_payload_sha256"] = rows[0].get("expected_sha256")
                if integrity != "PASS":
                    block("P0_FREEZE_INVALID", rows[0]["reason"] or integrity)
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
                block("P0_FREEZE_INVALID", f"Verifier rejected P0: {type(exc).__name__}: {exc}")
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
                report_raw = budget.read(root, report_path)
                report = _json(report_raw, budget)
                if not isinstance(report, dict) or report.get("operational_night") != night:
                    block("PDCA_REPORT_INVALID", "Report schema/night mismatch")
                else:
                    evidence["pdca_overall_status"] = report.get("overall_status")
                    evidence["pdca_run_id"] = report.get("run_id")
                    stages = report.get("stages")
                    valid_members = isinstance(stages, list) and all(isinstance(s, dict) for s in stages)
                    names = [s.get("name") for s in stages] if valid_members else []
                    if not valid_members:
                        block("PDCA_REPORT_INVALID", "Canonical parent stages must be a list of objects")
                    elif len(names) != len(STAGE_NAMES) or set(names) != set(STAGE_NAMES):
                        block("PDCA_STAGES_INCOMPLETE", "Canonical nine parent stages absent or duplicated")
                    elif any(s.get("status") != "PASS" for s in stages):
                        block("PDCA_SCIENTIFIC_GATES_OPEN", "One or more required canonical stages are not PASS")
                    if report.get("overall_status") != "PASS" or report.get("completed") is not True:
                        block("PDCA_NOT_COMPLETED", "Parent has not certified an all-stage successful run")
                    run_id = report.get("run_id")
                    if not isinstance(run_id, str) or not re.fullmatch("[0-9a-f]{64}", run_id):
                        block("PDCA_RUN_ID_INVALID", "Missing source-bound master run identifier")
                    else:
                        stored_path = f"reports/pdca/{night}/runs/{run_id}/run_manifest.json"
                        stored = _prediction_path(root, stored_path)
                        if (not stored.is_file() or budget.read(root, stored_path) != report_raw or
                                budget.read(root, report_path) != report_raw):
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
