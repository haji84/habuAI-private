#!/usr/bin/env python3
"""Restore a byte-exact GPX from split base64 XZ archive parts."""

from __future__ import annotations
import argparse, base64, hashlib, json, lzma
from pathlib import Path

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def restore(parts_dir: Path, manifest_path: Path, output: Path) -> dict:
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    parts=sorted(parts_dir.glob("part_*.b64"))
    if not parts:
        raise FileNotFoundError(f"no archive parts in {parts_dir}")
    encoded="".join(p.read_text(encoding="ascii").strip() for p in parts)
    compressed=base64.b64decode(encoded, validate=True)
    if len(compressed)!=manifest["xz_size_bytes"]:
        raise ValueError("xz size mismatch")
    if sha256_bytes(compressed)!=manifest["xz_sha256"]:
        raise ValueError("xz SHA-256 mismatch")
    raw=lzma.decompress(compressed)
    if len(raw)!=manifest["raw_size_bytes"]:
        raise ValueError("raw size mismatch")
    if sha256_bytes(raw)!=manifest["raw_sha256"]:
        raise ValueError("raw SHA-256 mismatch")
    if b"<trkpt" not in raw:
        raise ValueError("restored payload has no GPX track points")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(raw)
    return {"output":str(output),"raw_sha256":manifest["raw_sha256"],"parts":len(parts),"byte_exact":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--parts-dir",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(restore(args.parts_dir,args.manifest,args.output),ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
