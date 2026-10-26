#!/usr/bin/env python3
"""Verify exact uploaded Guru Maps GPX bytes; never infer a missing road track."""
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "incoming/gpx"
CASES = (
    ("2026-10-24-0723_unnamed.original.gpx", 53241,
     "ab20c54e4fb7083156933629aec8259899b7c4bac5ba30a3112502da7686f314", 202),
    ("2026-10-24-0834_unnamed.original.gpx.parts", 5468818,
     "e7a93f4046ec114f3e191ee0bbe49fd238129913f29620147243cac993fce7f1", 20689),
)

def verify():
    out = []
    for relative, expected_size, expected_sha, expected_count in CASES:
        path = SRC / relative
        if path.is_file():
            content = path.read_bytes()
        else:
            files = sorted(path.glob("part_???.gpxfrag"))
            if [f.name for f in files] != [f"part_{i:03d}.gpxfrag" for i in range(21)]:
                raise RuntimeError("Incomplete, duplicate or reordered GPX source shards")
            content = b"".join(f.read_bytes() for f in files)
        if len(content) != expected_size:
            raise RuntimeError("GPX byte count mismatch: " + relative)
        sha = hashlib.sha256(content).hexdigest()
        if sha != expected_sha:
            raise RuntimeError("Original GPX source SHA-256 changed: " + relative)
        root = ET.fromstring(content)
        count = sum(n.tag.endswith("}trkpt") or n.tag == "trkpt" for n in root.iter())
        if count != expected_count:
            raise RuntimeError("Original GPX location point count mismatch: " + relative)
        out.append((relative, sha, count))
    return out

if __name__ == "__main__":
    for path, sha, count in verify():
        print(f"PASS: {path} {count} original GPS points SHA256 {sha}")
    print("No interpolated missing track is created; no Negative labels are issued.")
