#!/usr/bin/env python3
"""Audit a newly received raw Habu AI file without altering it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_EXTENSIONS = {
    "gpx": {".gpx"},
    "habu_log": {".txt", ".csv", ".xlsx", ".json"},
    "capture_db": {".csv", ".xlsx", ".json"},
    "gis": {".zip", ".xml", ".gml", ".geojson", ".json", ".csv", ".parquet", ".pbf"},
    "other": set(),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_file(path: Path, kind: str, manifest: Path | None = None) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(path)
    if kind not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported kind: {kind}")
    allowed = ALLOWED_EXTENSIONS[kind]
    if allowed and path.suffix.lower() not in allowed:
        raise ValueError(f"extension {path.suffix!r} is not allowed for {kind}")

    digest = sha256_file(path)
    duplicate_paths: list[str] = []
    if manifest and manifest.exists():
        with manifest.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if row.get("sha256", "").lower() == digest:
                    duplicate_paths.append(row.get("path", ""))

    return {
        "path": path.as_posix(),
        "filename": path.name,
        "kind": kind,
        "bytes": path.stat().st_size,
        "sha256": digest,
        "received_at_utc": datetime.now(timezone.utc).isoformat(),
        "duplicate": bool(duplicate_paths),
        "duplicate_paths": duplicate_paths,
        "status": "duplicate_review_required" if duplicate_paths else "unreviewed_incoming",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=sorted(ALLOWED_EXTENSIONS))
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_file(args.file, args.kind, args.manifest), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

