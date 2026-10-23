#!/usr/bin/env python3
"""Read-only SHA-256 and ZIP integrity check for the OSM road-grid archive.

This verifies archived bytes as data, NOT that OSM auxiliary roads or their
terrain features have become a reviewed production ForecastUniverse.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PART_DIR = "artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts"
EXPECTED_SHA256 = "f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17"
EXPECTED_PARTS = 33
MAX_ENCODED = 12 * 1024 * 1024
MAX_MEMBER_SUM = 500 * 1024 * 1024
MAX_MEMBERS = 200


class ArchiveVerificationError(ValueError):
    pass


def verify_archive(root: Path, *, expected_sha256: str = EXPECTED_SHA256) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ArchiveVerificationError("Invalid expected archive checksum")
    directory = Path(root) / PART_DIR
    if not directory.is_dir():
        raise ArchiveVerificationError("No archived OSM source parts")
    paths = sorted(directory.glob("part_*.b64"))
    if len(paths) != EXPECTED_PARTS or [p.name for p in paths] != [
        f"part_{i:03d}.b64" for i in range(EXPECTED_PARTS)
    ]:
        raise ArchiveVerificationError("Missing, duplicated or unexpected OSM parts")
    chunks, size = [], 0
    for part in paths:
        if part.is_symlink() or not part.is_file():
            raise ArchiveVerificationError("Unsafe source part")
        chunk = part.read_bytes()
        size += len(chunk)
        if size > MAX_ENCODED:
            raise ArchiveVerificationError("OSM archive parts exceed byte budget")
        chunks.append(chunk)
    encoded = b"".join(chunks)
    encoded = b"".join(encoded.split())
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ArchiveVerificationError("OSM archive base64 invalid") from exc
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise ArchiveVerificationError("OSM archive SHA256 mismatch")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw), "r")
    except (ValueError, zipfile.BadZipFile) as exc:
        raise ArchiveVerificationError("OSM archive ZIP invalid") from exc
    with zf:
        members = zf.infolist()
        if not members or len(members) > MAX_MEMBERS:
            raise ArchiveVerificationError("Unreasonable OSM ZIP member count")
        total = 0
        names = set()
        for entry in members:
            name = PurePosixPath(entry.filename)
            if (entry.filename.startswith("/") or "\\" in entry.filename or
                    name.is_absolute() or ".." in name.parts or not entry.filename or
                    entry.filename in names):
                raise ArchiveVerificationError("Unsafe ZIP member path")
            names.add(entry.filename)
            mode = (entry.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise ArchiveVerificationError("ZIP symlink prohibited")
            total += entry.file_size
            if total > MAX_MEMBER_SUM:
                raise ArchiveVerificationError("OSM ZIP inflated byte budget exceeded")
        corrupt = zf.testzip()
        if corrupt is not None:
            raise ArchiveVerificationError("ZIP member CRC error: " + corrupt)
        filenames = sorted(entry.filename for entry in members if not entry.is_dir())
    return {
        "status": "ARCHIVE_INTEGRITY_VERIFIED_AUXILIARY_ONLY",
        "source_type": "OpenStreetMap auxiliary road grid",
        "sha256": actual,
        "part_count": len(paths),
        "archive_bytes": len(raw),
        "file_count": len(filenames),
        "filenames": filenames,
        "road_forecast_universe_certified": False,
        "per_road_dem_features_certified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = verify_archive(args.repo_root)
    except (ArchiveVerificationError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
