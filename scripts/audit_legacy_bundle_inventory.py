#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE_COMMIT="8fc8cdb81e9b8da566ba1e57ed1d52e7d0627475"
SOURCE_URL=(
    "https://raw.githubusercontent.com/haji84/habuAI/"
    f"{SOURCE_COMMIT}/data/raw/habuAI_initial_raw_bundle.zip"
)
SOURCE_GIT_BLOB_SHA1="01e612df1ed56e198116ec3e882786da34e4e232"
SOURCE_SIZE=4_897_166

def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii")+raw).hexdigest()

def download() -> bytes:
    req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"habuAI-private-bundle-audit/1"})
    with urllib.request.urlopen(req,timeout=120) as r:
        return r.read()

def classify(name: str) -> str:
    low=name.lower()
    if low.endswith(".gpx"): return "gpx"
    if low.endswith(".txt"): return "text"
    if low.endswith(".csv"): return "csv"
    if low.endswith(".xlsx") or low.endswith(".xls"): return "spreadsheet"
    if low.endswith(".json"): return "json"
    return "other"

def audit(raw: bytes) -> dict:
    if len(raw)!=SOURCE_SIZE:
        raise ValueError(f"source size mismatch: {len(raw)}")
    blob=git_blob_sha1(raw)
    if blob!=SOURCE_GIT_BLOB_SHA1:
        raise ValueError(f"source blob mismatch: {blob}")
    members=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        bad=z.testzip()
        if bad is not None:
            raise ValueError(f"ZIP CRC failure: {bad}")
        for info in z.infolist():
            if info.is_dir(): continue
            data=z.read(info)
            members.append({
                "path":info.filename,
                "kind":classify(info.filename),
                "size_bytes":len(data),
                "sha256":hashlib.sha256(data).hexdigest(),
            })
    kinds={}
    for m in members:
        kinds[m["kind"]]=kinds.get(m["kind"],0)+1
    return {
        "schema_version":"legacy-initial-bundle-inventory-v1",
        "audited_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":{
            "repository":"haji84/habuAI",
            "commit":SOURCE_COMMIT,
            "path":"data/raw/habuAI_initial_raw_bundle.zip",
            "size_bytes":len(raw),
            "git_blob_sha1":blob,
            "sha256":hashlib.sha256(raw).hexdigest(),
        },
        "member_count":len(members),
        "counts_by_kind":kinds,
        "members":members,
    }

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=Path("evidence/legacy/habuAI-public/initial_bundle_inventory.json"))
    args=ap.parse_args()
    report=audit(download())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"member_count":report["member_count"],"counts_by_kind":report["counts_by_kind"]},ensure_ascii=False))

if __name__=="__main__":
    main()
