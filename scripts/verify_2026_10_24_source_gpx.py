#!/usr/bin/env python3
"""Verify and reconstruct byte-exact 2026-10-24 Guru Maps GPX originals.

The owner uploaded TWO independent real GPX segments with a 67m34s gap.
Do not interpolate this gap or turn road guesses into GPS samples/Negative.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("incoming/gpx/2026-10-24/source-manifest.json")


class OriginalGpxError(ValueError):
    pass


def _digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _safe_read(root: Path, rel: str) -> bytes:
    p = root / rel
    if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root.resolve()):
        raise OriginalGpxError("Source file path is missing/unsafe: " + rel)
    return p.read_bytes()


def verify(root: Path = ROOT, output: Path | None = None) -> dict:
    root = root.resolve()
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "habu-reversible-original-gpx-intake-2026-10-24-v1":
        raise OriginalGpxError("Unexpected original GPX source schema")
    source = manifest.get("original_files", [])
    if len(source) != 2 or manifest.get("gps_gap", {}).get("unmeasured_seconds") != 4054:
        raise OriginalGpxError("Expected two original recordings and measured gap")
    first = source[0]
    a = _safe_read(root, first["path"])
    if len(a) != first["bytes"] or _digest(a) != first["sha256"]:
        raise OriginalGpxError("Original segment A SHA/size mismatch")
    second = source[1]
    chunks = second["parts"]
    if len(chunks) != 21:
        raise OriginalGpxError("Need exactly 21 source chunks")
    all_parts: list[bytes] = []
    for idx, chunk in enumerate(chunks):
        if not chunk["path"].endswith("part_%03d.gpxbytes" % idx):
            raise OriginalGpxError("Source part order mismatch")
        b = _safe_read(root, chunk["path"])
        if len(b) != chunk["bytes"] or _digest(b) != chunk["sha256"]:
            raise OriginalGpxError("Source part SHA/size mismatch at %d" % idx)
        all_parts.append(b)
    b = b"".join(all_parts)
    if len(b) != second["bytes"] or _digest(b) != second["sha256"]:
        raise OriginalGpxError("Reassembled original segment B SHA/size mismatch")

    expected_gpx = {str(i): src["gps_points"] for i, src in enumerate(source)}
    actual = {}
    time_spans = []
    for i, raw in enumerate((a, b)):
        try:
            xml = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise OriginalGpxError("Invalid original GPX XML") from exc
        points = [el for el in xml.iter() if el.tag.split("}")[-1] == "trkpt"]
        if len(points) != expected_gpx[str(i)]:
            raise OriginalGpxError("Original GPX point count mismatch")
        stamps = [
            el.text for pt in points for el in pt
            if el.tag.split("}")[-1] == "time"
        ]
        if len(stamps) != len(points):
            raise OriginalGpxError("Original GPS timestamps missing")
        time_spans.append((datetime.fromisoformat(stamps[0].replace("Z", "+00:00")),
                           datetime.fromisoformat(stamps[-1].replace("Z", "+00:00"))))
        actual[str(i)] = len(points)
    gap = (time_spans[1][0] - time_spans[0][1]).total_seconds()
    if abs(gap - 4054) > 1:
        raise OriginalGpxError("Time gap no longer agrees with owner measured GPX")
    if output is not None:
        dest = output.resolve()
        if dest.is_relative_to(root / "data/raw") or dest.is_relative_to(root / "predictions/original"):
            raise OriginalGpxError("Cannot overwrite Git-tracked canonical raw or ORIGINAL")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and _digest(dest.read_bytes()) != _digest(b):
            raise OriginalGpxError("Refusing output overwrite with mismatched content")
        dest.write_bytes(b)
    return {
        "status": "ORIGINAL_BYTES_VERIFIED",
        "night": "2026-10-24",
        "source_sha256": [first["sha256"], second["sha256"]],
        "original_point_counts": actual,
        "verified_original_gpx_bytes": len(a) + len(b),
        "verified_unmeasured_gap_seconds": gap,
        "restored_only_original_segment_B": output is not None,
        "interpolation_performed": False,
        "eligible_negative_labels": 0,
        "formal_pdca_prediction_score": "BLOCKED_NO_ORIGINAL_P0",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--write-original-b", type=Path,
                    help="Optional output for reassembled *unchanged* original GPX B.")
    a = ap.parse_args()
    print(json.dumps(verify(a.root, a.write_original_b), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
