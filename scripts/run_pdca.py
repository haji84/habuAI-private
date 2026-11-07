#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT)]

JST = ZoneInfo("Asia/Tokyo")

def operational_night(now: datetime) -> str:
    local = now.astimezone(JST)
    if local.hour < 7:
        from datetime import timedelta
        local -= timedelta(days=1)
    return local.date().isoformat()

def main() -> int:
    ap = argparse.ArgumentParser(description="Run the complete Habu AI PDCA pipeline.")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--night", help="Operational night YYYY-MM-DD. Defaults using the 07:00 JST boundary.")
    ap.add_argument("--output", type=Path, help="Optional extra JSON output path.")
    ap.add_argument("--budget-seconds", type=int,
                    help="Master budget (default 300); private scoring budget 1..30 (default 30).")
    ap.add_argument("--bridge-context", type=Path, help=argparse.SUPPRESS)
    ap.add_argument("--private-individual-request-path",
                    help="Explicit private read-only scoring mode: existing typed request path relative to --root; no publication, fitting or master execution.")
    ap.add_argument("--private-individual-request-sha256",
                    help="Exact SHA-256 paired with the private request path; requires existing frozen ORIGINAL and typed evidence, grants no official authority.")
    args = ap.parse_args()

    private_mode = (args.private_individual_request_path is not None or
                    args.private_individual_request_sha256 is not None)
    if private_mode:
        if not args.private_individual_request_path or not args.private_individual_request_sha256:
            ap.error("Private individual scoring requires both request path and SHA-256.")
        if not args.night:
            ap.error("Private individual scoring requires an explicit --night.")
        if args.output is not None or args.bridge_context is not None:
            ap.error("Private individual scoring forbids --output and --bridge-context.")
        budget = 30 if args.budget_seconds is None else args.budget_seconds
        if not 1 <= budget <= 30:
            ap.error("Private individual scoring budget must be 1..30 seconds.")
        # Fixed sibling: a regular external "scripts" package can shadow our
        # namespace package even when the repository root is first on sys.path.
        from score_private_pdca_individual_targets import score_private_individual_targets
        result = score_private_individual_targets(
            args.root, night=args.night, request_path=args.private_individual_request_path,
            request_sha256=args.private_individual_request_sha256, budget_seconds=budget)
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        if result['execution_status'] == 'FAIL':
            return 1
        return 2 if result['execution_status'] in {'DATA_BLOCKED', 'RUNTIME_BLOCKED'} else 0

    night = args.night or operational_night(datetime.now(JST))
    # The durable parent uses POSIX locking. A blocked invocation is not
    # a master run and must never write a compatibility result or --output.
    try:
        from master_orchestrator import run_master
    except ModuleNotFoundError as exc:
        if exc.name != 'fcntl':
            raise
        from master_contracts import validate_night
        try:
            validate_night(night)
        except ValueError as exc:
            ap.error(str(exc))
        print(json.dumps({
            'schema_version': 'habu-pdca-runtime-block-v1',
            'operational_night': night,
            'overall_status': 'BLOCKED',
            'execution_status': 'RUNTIME_BLOCKED',
            'completed': False,
            'blockers': ['PDCA_POSIX_RUNTIME_UNAVAILABLE'],
        }, ensure_ascii=True, allow_nan=False))
        return 2
    if args.budget_seconds is None:
        args.budget_seconds = 300
    options = {}
    if args.bridge_context:
        from pdca_bridge import checkpoint_publisher, SCIENTIFIC_BUDGET
        if args.budget_seconds != SCIENTIFIC_BUDGET:
            raise ValueError("Bridge scientific budget is fixed at 300 seconds")
        callback, context = checkpoint_publisher(args.bridge_context)
        options = {"checkpoint_callback": callback,
                   "budget_floor": context["attempt"]["base_elapsed"],
                   "attempt_deadline": context["attempt"]["deadline"]}
    result = run_master(args.root.resolve(), night, args.budget_seconds, **options)
    payload = json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 2 if result["overall_status"] in {"BLOCKED", "FAIL"} else 0

if __name__ == "__main__":
    raise SystemExit(main())
