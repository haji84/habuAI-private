#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pdca_pipeline import canonical_prediction_hash, parse_dt, night_for, _targets

JST=ZoneInfo("Asia/Tokyo")

def next_version(base: Path) -> str:
    nums=[]
    if base.exists():
        for p in base.iterdir():
            if p.is_dir() and p.name.startswith("P") and p.name[1:].isdigit():
                nums.append(int(p.name[1:]))
    if sorted(nums) != list(range(len(nums))):
        raise ValueError("existing prediction versions are not contiguous")
    return f"P{len(nums)}"

def freeze(root: Path, input_path: Path, night: str, version: str|None=None, *, now: datetime | None = None) -> Path:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", night) or date.fromisoformat(night).isoformat() != night:
        raise ValueError("night must be a valid ISO date")
    payload=json.loads(input_path.read_text(encoding="utf-8"))
    base=root/"predictions"/"original"/night
    ver=version or next_version(base)
    if not re.fullmatch(r"P(0|[1-9][0-9]*)", ver):
        raise ValueError("version must be P0, P1, P2...")
    dest=base/ver
    if dest.exists():
        raise FileExistsError(f"{dest} already exists; frozen versions are immutable")
    if ver != next_version(base):
        raise ValueError("versions must be appended in sequence starting at P0")
    for field, expected in (("prediction_class", "ORIGINAL"), ("operational_night", night), ("prediction_version", ver)):
        if field in payload and payload[field] != expected:
            raise ValueError(f"{field} conflicts with issuance")
    if payload.get("freeze_status") or payload.get("frozen_at"):
        raise ValueError("previously frozen/recovered records cannot be reissued")
    issued_at = now if now is not None else datetime.now(JST)
    if issued_at.tzinfo is None:
        raise ValueError("issuance clock must be timezone aware")
    issued_at = issued_at.astimezone(JST)
    if night_for(issued_at) > night:
        raise ValueError("cannot issue predictions for a completed operational night")
    # Information cutoff may precede model computation; it never establishes issuance.
    if "cutoff_time" in payload and parse_dt(str(payload["cutoff_time"])) > issued_at:
        raise ValueError("cutoff_time cannot follow actual issuance time")
    if "created_at" in payload and parse_dt(str(payload["created_at"])) != issued_at:
        raise ValueError("created_at must equal actual issuance time")
    targets = _targets(payload)
    if len(targets) != len(payload.get("targets_100m_10min") or payload.get("targets") or []):
        raise ValueError("invalid prediction target")
    for t in targets:
        if t["time"] <= issued_at or night_for(t["time"]) != night:
            raise ValueError("targets must be prospective and belong to the issued night")
    now=issued_at.isoformat()
    payload["provenance_status"] = "NOT_VALIDATED"
    payload["strict_official_score_eligible"] = False
    payload["operational_night"]=night
    payload["prediction_version"]=ver
    payload["prediction_class"]="ORIGINAL"
    payload.setdefault("created_at",now)
    payload.setdefault("cutoff_time",now)
    payload["timezone"]="Asia/Tokyo"
    payload["frozen_at"]=now
    payload.pop("payload_sha256",None)
    payload["payload_sha256"]=canonical_prediction_hash(payload)
    dest.mkdir(parents=True,exist_ok=False)
    target=dest/"prediction.json"
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (dest/"sha256.txt").write_text(payload["payload_sha256"]+"  prediction.json\n",encoding="utf-8")
    return target

def main() -> int:
    ap=argparse.ArgumentParser(description="Freeze an immutable ORIGINAL Habu AI prediction version.")
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--night",required=True)
    ap.add_argument("--version",help="Optional explicit P0/P1/...; default is next version.")
    ap.add_argument("--root",type=Path,default=ROOT)
    args=ap.parse_args()
    target=freeze(args.root.resolve(),args.input,args.night,args.version)
    print(target)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
