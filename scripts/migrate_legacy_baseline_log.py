#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from scripts.ingest_attachment import ingest_attachment

SOURCE_COMMIT="8fc8cdb81e9b8da566ba1e57ed1d52e7d0627475"
SOURCE_URL=(
    "https://raw.githubusercontent.com/haji84/habuAI/"
    f"{SOURCE_COMMIT}/data/raw/habuAI_initial_raw_bundle.zip"
)
SOURCE_GIT_BLOB_SHA1="01e612df1ed56e198116ec3e882786da34e4e232"
SOURCE_SIZE=4_897_166
MEMBER="data/raw/logs/baseline_through_2026-08-27.txt"
EXPECTED_SHA256="3326081068714144bbb1c9654edd58d56bd92ad0c238fde88e991fa1c4e2fcc3"
EXPECTED_SIZE=93_597

def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii")+raw).hexdigest()

def download() -> bytes:
    req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"habuAI-private-log-migrate/1"})
    with urllib.request.urlopen(req,timeout=120) as r:
        return r.read()

def extract(raw_bundle: bytes) -> bytes:
    if len(raw_bundle)!=SOURCE_SIZE:
        raise ValueError("source bundle size mismatch")
    if git_blob_sha1(raw_bundle)!=SOURCE_GIT_BLOB_SHA1:
        raise ValueError("source bundle blob mismatch")
    with zipfile.ZipFile(io.BytesIO(raw_bundle)) as z:
        data=z.read(MEMBER)
    if len(data)!=EXPECTED_SIZE:
        raise ValueError("baseline log size mismatch")
    digest=hashlib.sha256(data).hexdigest()
    if digest!=EXPECTED_SHA256:
        raise ValueError(f"baseline log SHA mismatch: {digest}")
    return data

def migrate(repo_root: Path) -> dict:
    data=extract(download())
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"baseline_through_2026-08-27.txt"
        p.write_bytes(data)
        return ingest_attachment(
            p,
            repo_root=repo_root,
            kind="habu_log",
            source="legacy-public-bundle",
            source_ref=f"haji84/habuAI@{SOURCE_COMMIT}:{MEMBER}",
            expected_sha256=EXPECTED_SHA256,
            promote=True,
        )

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    args=ap.parse_args()
    result=migrate(args.repo_root.resolve())
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
