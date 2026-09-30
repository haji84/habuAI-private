#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pdca_pipeline import canonical_prediction_hash

JST=ZoneInfo("Asia/Tokyo")

def next_version(base: Path) -> str:
    nums=[]
    if base.exists():
        for p in base.iterdir():
            if p.is_dir() and p.name.startswith("P") and p.name[1:].isdigit():
                nums.append(int(p.name[1:]))
    return f"P{max(nums)+1}" if nums else "P0"

def freeze(root: Path, input_path: Path, night: str, version: str|None=None) -> Path:
    payload=json.loads(input_path.read_text(encoding="utf-8"))
    base=root/"predictions"/"original"/night
    ver=version or next_version(base)
    if not (ver.startswith("P") and ver[1:].isdigit()):
        raise ValueError("version must be P0, P1, P2...")
    dest=base/ver
    if dest.exists():
        raise FileExistsError(f"{dest} already exists; frozen versions are immutable")
    now=datetime.now(JST).isoformat()
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
