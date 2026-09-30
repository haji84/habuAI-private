#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pdca_pipeline import run_pipeline

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
    args = ap.parse_args()

    night = args.night or operational_night(datetime.now(JST))
    result = run_pipeline(args.root.resolve(), night)
    payload = json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 2 if result["overall_status"] in {"BLOCKED", "FAIL"} else 0

if __name__ == "__main__":
    raise SystemExit(main())
