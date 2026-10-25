#!/usr/bin/env python3
"""Read-only, fail-closed preflight for the next ORIGINAL P0 forecast.

This command does not issue, freeze, modify or backdate predictions. It reports
why today's reviewed production path cannot yet satisfy the official P0 contract.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from champion_registry import AUTHORITY_BLOCKER, SCOPE
from master_contracts import validate_night

JST = ZoneInfo("Asia/Tokyo")


def operational_night(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An aware timestamp is required")
    local = value.astimezone(JST)
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()


def inspect(root: Path, night: str, *, now: datetime,
            planned_start: datetime | None = None) -> dict:
    validate_night(night)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Current time must have a timezone")
    root = Path(root).resolve()
    local_now = now.astimezone(JST)
    issues = []

    def block(code: str, detail: str) -> None:
        issues.append({"code": code, "detail": detail})

    if planned_start is None:
        block("PRE_EXPLORATION_START_UNKNOWN",
              "A verified planned exploration start is required to establish P0 < start.")
    else:
        if planned_start.tzinfo is None or planned_start.utcoffset() is None:
            raise ValueError("Planned start must have a timezone")
        if operational_night(planned_start) != night:
            block("START_NIGHT_MISMATCH", "Planned start is not in the requested 07:00 JST night.")
        if planned_start <= now:
            block("START_NOT_FUTURE", "Cannot issue a pre-departure prediction after planned start.")
    # A month aggregate, a chat estimate or a retrospective GPX is never ex-ante proof.
    if operational_night(now) > night:
        block("HISTORICAL_NIGHT", "Past nights cannot receive retroactive ORIGINAL P0 versions.")

    folder = root / "predictions" / "original" / night / "P0"
    p0_exists = folder.exists()
    if p0_exists:
        block("ORIGINAL_P0_ALREADY_EXISTS",
              "Existing ORIGINAL P0 must be audited, never overwritten or reissued.")

    # Current reviewed champion registry is sandbox only. A claim in JSON or
    # an environment variable cannot authorize real production issuance.
    if SCOPE == "SANDBOX_MECHANICS":
        block("PRODUCTION_ISSUANCE_AUTHORITY_BLOCKED", AUTHORITY_BLOCKER)
    else:
        block("PRODUCTION_ISSUANCE_NOT_ATTESTED",
              "No reviewed trusted production authority attestation in this preflight.")

    block("EX_ANTE_INPUT_BUNDLE_NOT_ATTESTED",
          "No verified weather/terrain/road/forecast-universe/feature snapshot and availability ledger was provided.")
    block("FORMAL_PREDICTION_OUTPUT_NOT_ATTESTED",
          "No trusted prospective 1km through 100m x 10min result and A/B/C route contract was executed.")

    return {
        "schema_version": "habu-p0-readiness-v1",
        "operational_night": night,
        "timezone": "Asia/Tokyo",
        "checked_at": local_now.isoformat(),
        "planned_start": planned_start.astimezone(JST).isoformat() if planned_start else None,
        "status": "BLOCKED",
        "official_original_p0_issued": False,
        "existing_p0_directory": p0_exists,
        "official_stage_gate_scored": False,
        "read_only": True,
        "blockers": issues,
        "next_action": "Implement verified production authority and ex-ante input/model issuance; then rerun strict preflight before any P0 freeze.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--night", required=True,
                        help="07:00 JST operational night YYYY-MM-DD")
    parser.add_argument("--planned-start",
                        help="Actual proposed search start ISO-8601 with timezone")
    args = parser.parse_args()
    start = datetime.fromisoformat(args.planned_start) if args.planned_start else None
    result = inspect(args.root, args.night, now=datetime.now(JST), planned_start=start)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
