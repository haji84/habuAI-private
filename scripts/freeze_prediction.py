#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import tempfile
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pdca_pipeline import canonical_prediction_hash, parse_dt, night_for, _targets
from master_contracts import canonical_bytes, safe_path

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

LINEAGE_FIELDS = {'champion_id', 'registry_event_id', 'inference_sha256', 'inference_adapter',
                  'issued_at', 'qualification', 'generated_by'}


def _validate_payload(payload, night, issued_at):
    if not isinstance(payload, dict):
        raise ValueError("Prediction must be an object")
    canonical_bytes(payload)  # reject NaN/Infinity before any immutable publication
    if issued_at.tzinfo is None:
        raise ValueError("issuance clock must be timezone aware")
    if night_for(issued_at) > night:
        raise ValueError("cannot issue predictions for a completed operational night")
    if "cutoff_time" in payload and parse_dt(str(payload["cutoff_time"])) > issued_at:
        raise ValueError("cutoff_time cannot follow actual issuance time")
    if "created_at" in payload and parse_dt(str(payload["created_at"])) != issued_at:
        raise ValueError("created_at must equal actual issuance time")
    if payload.get("freeze_status") or payload.get("frozen_at"):
        raise ValueError("previously frozen/recovered records cannot be reissued")
    targets = _targets(payload)
    if len(targets) != len(payload.get("targets_100m_10min") or payload.get("targets") or []):
        raise ValueError("invalid prediction target")
    for t in targets:
        if t["time"] <= issued_at or night_for(t["time"]) != night:
            raise ValueError("targets must be prospective and belong to the issued night")


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _freeze_payload(root, payload, night, version=None, *, clock, namespace='predictions/original',
                    before_publish=None, lineage=None):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", night) or date.fromisoformat(night).isoformat() != night:
        raise ValueError("night must be a valid ISO date")
    root = Path(root).absolute()
    lock_path = safe_path(root, '.prediction-issuance.lock')
    # The existing parent is the durability boundary; do not create ancestors
    # outside the directory chain synced before publication.
    if not root.parent.is_dir():
        raise ValueError('Prediction root parent must already exist')
    root.mkdir(exist_ok=True)
    with lock_path.open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        issued_at = clock()
        if issued_at.tzinfo is None:
            raise ValueError("issuance clock must be timezone aware")
        issued_at = issued_at.astimezone(JST)
        _validate_payload(payload, night, issued_at)
        if before_publish:
            before_publish(issued_at)
        base = safe_path(root, namespace+'/'+night)
        ver = version or next_version(base)
        if not re.fullmatch(r"P(0|[1-9][0-9]*)", ver):
            raise ValueError("version must be P0, P1, P2...")
        dest = base/ver
        if dest.exists():
            raise FileExistsError(f"{dest} already exists; frozen versions are immutable")
        if ver != next_version(base):
            raise ValueError("versions must be appended in sequence starting at P0")
        for field, expected in (("prediction_class", "ORIGINAL"), ("operational_night", night), ("prediction_version", ver)):
            if field in payload and payload[field] != expected:
                raise ValueError(f"{field} conflicts with issuance")
        record = dict(payload)
        record.update(operational_night=night, prediction_version=ver, prediction_class="ORIGINAL",
                      provenance_status="NOT_VALIDATED", strict_official_score_eligible=False,
                      timezone="Asia/Tokyo", frozen_at=issued_at.isoformat())
        record.setdefault('created_at', issued_at.isoformat())
        record.setdefault('cutoff_time', issued_at.isoformat())
        if lineage:
            record.update(lineage)
            record['issued_at'] = issued_at.isoformat()
        record.pop('payload_sha256', None)
        record['payload_sha256'] = canonical_prediction_hash(record)
        raw = canonical_bytes(record)+b'\n'
        base.mkdir(parents=True, exist_ok=True)
        # Persist each directory link, including newly created output/root parents.
        # Re-sync on retry too: a prior sync failure may have left visible directories.
        parent = base.parent
        while True:
            _sync_directory(parent)
            if parent == root.parent:
                break
            parent = parent.parent
        temporary = Path(tempfile.mkdtemp(prefix='.pending-', dir=base))
        try:
            for name, data in [('prediction.json', raw), ('sha256.txt', (record['payload_sha256']+'  prediction.json\n').encode())]:
                with (temporary/name).open('xb') as stream:
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
            _sync_directory(temporary)
            if before_publish:
                before_publish(clock())
            else:
                # Publication can follow staging; never backdate an expired forecast.
                check = dict(payload); check.pop('created_at', None)
                _validate_payload(check, night, clock())
            if dest.exists():
                raise FileExistsError('Immutable prediction destination already exists')
            os.rename(temporary, dest)
            _sync_directory(base)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return dest/'prediction.json'


def freeze(root: Path, input_path: Path, night: str, version: str|None=None, *, now: datetime | None = None) -> Path:
    payload = json.loads(input_path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or LINEAGE_FIELDS.intersection(payload):
        raise ValueError('Generic external records cannot claim executed Champion lineage')
    clock = (lambda: now) if now is not None else (lambda: datetime.now(JST))
    return _freeze_payload(root, payload, night, version, clock=clock)

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
