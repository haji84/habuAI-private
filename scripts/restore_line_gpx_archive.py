#!/usr/bin/env python3
"""Restore a byte-exact GPX from line-preserving UTF-8 archive parts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def restore(parts_dir: Path, manifest_path: Path, output: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parts = sorted(parts_dir.glob("part_*.txt"))
    if len(parts) != manifest["part_count"]:
        raise ValueError(
            f"part count mismatch: expected {manifest['part_count']}, got {len(parts)}"
        )

    # files.read preserves the original GPX line text but omits the separator
    # between separately materialized ranges. Reinsert exactly one LF at each
    # archive-part boundary. The source GPX is LF-only and has no final LF.
    text = "\n".join(part.read_text(encoding="utf-8") for part in parts)
    raw = text.encode("utf-8")

    if len(raw) != manifest["raw_size_bytes"]:
        raise ValueError(
            f"raw size mismatch: expected {manifest['raw_size_bytes']}, got {len(raw)}"
        )
    digest = sha256_bytes(raw)
    if digest != manifest["raw_sha256"]:
        raise ValueError(
            f"raw SHA-256 mismatch: expected {manifest['raw_sha256']}, got {digest}"
        )

    root = ET.fromstring(raw)
    ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
    trkpt_count = len(root.findall(".//gpx:trkpt", ns))
    if trkpt_count != manifest["trackpoint_count"]:
        raise ValueError(
            f"trackpoint count mismatch: expected {manifest['trackpoint_count']}, got {trkpt_count}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {
        "byte_exact": True,
        "raw_size_bytes": len(raw),
        "raw_sha256": digest,
        "trackpoint_count": trkpt_count,
        "part_count": len(parts),
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parts-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            restore(args.parts_dir, args.manifest, args.output),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
