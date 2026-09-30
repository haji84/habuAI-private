#!/usr/bin/env python3
"""Single-entry Habu AI PDCA orchestrator.

This coordinator is deliberately fail-closed: a stage is BLOCKED until its
required evidence and executable implementation are available.
"""
from __future__ import annotations
import argparse, json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

@dataclass
class Stage:
    name: str
    status: str
    reason: str = ""

def operational_night(now: datetime) -> str:
    local = now.astimezone(JST)
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()

def prediction_root(root: Path, night: str) -> Path:
    return root / "predictions" / "original" / night

def discover_predictions(root: Path, night: str) -> list[Path]:
    base = prediction_root(root, night)
    if not base.exists():
        return []
    versions = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("P")]
    return sorted(versions, key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 10**9)

def run(root: Path, night: str) -> dict:
    preds = discover_predictions(root, night)
    stages: list[Stage] = []
    if not preds:
        stages.append(Stage("load_frozen_predictions", "BLOCKED",
                            f"No ORIGINAL frozen predictions found for {night}"))
        for name in ("verify_prediction_integrity","load_actual_evidence","build_exposure",
                     "score_p0","score_realtime","error_analysis","walk_forward",
                     "candidate_validation","act_decision","persist_report"):
            stages.append(Stage(name, "BLOCKED", "Upstream frozen prediction dependency unavailable"))
    else:
        stages.append(Stage("load_frozen_predictions", "PASS",
                            "Found " + ", ".join(p.name for p in preds)))
        # Executable stage adapters are intentionally added only when their
        # evidence contracts are implemented and tested.
        for name in ("verify_prediction_integrity","load_actual_evidence","build_exposure",
                     "score_p0","score_realtime","error_analysis","walk_forward",
                     "candidate_validation","act_decision","persist_report"):
            stages.append(Stage(name, "BLOCKED", "Stage adapter not yet implemented"))

    return {
        "schema_version": "1.0",
        "operational_night": night,
        "prediction_scope": "ORIGINAL",
        "allow_replay": False,
        "generated_at": datetime.now(JST).isoformat(),
        "stages": [asdict(s) for s in stages],
        "overall_status": "PASS" if all(s.status == "PASS" for s in stages) else "BLOCKED",
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--night")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    night = args.night or operational_night(datetime.now(JST))
    result = run(args.root, night)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["overall_status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
