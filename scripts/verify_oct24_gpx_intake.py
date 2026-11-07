#!/usr/bin/env python3
"""Byte-exact verification of original 2026-10-24 Guru Maps GPX intake.

The second original GPX is safely archived in raw-line pieces solely because
the GitHub connector transfer cannot carry 5.5 MB in one request. This
verifier reassembles byte-exact source bytes in memory and refuses any mismatch.
It does not map-match, interpolate the GPS gap or generate training labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path("incoming/gpx/2026-10-24")
NS = "{http://www.topografix.com/GPX/1/1}"

class Oct24GPXSourceError(ValueError):
    pass

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()

def verify_gpx(data: bytes, expected: dict) -> dict:
    if len(data) != expected["size_bytes"] or digest(data) != expected["sha256"]:
        raise Oct24GPXSourceError("Original GPX byte length or SHA-256 mismatch")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise Oct24GPXSourceError("Source original GPX XML is damaged") from exc
    if root.tag != NS + "gpx" or root.attrib.get("version") != "1.1":
        raise Oct24GPXSourceError("Source is not declared GPX 1.1")
    points = list(root.iter(NS + "trkpt"))
    if len(points) != expected["raw_points"]:
        raise Oct24GPXSourceError("Raw original track-point count differs")
    times = [p.findtext(NS + "time") for p in points]
    if not times or None in times or times[0] != expected["first_time_utc"] or times[-1] != expected["last_time_utc"]:
        raise Oct24GPXSourceError("GPX source time envelope mismatch")
    stamps = [datetime.fromisoformat(t.replace("Z","+00:00")) for t in times]
    if any(stamp.tzinfo is None for stamp in stamps) or any(b <= a for a,b in zip(stamps,stamps[1:])):
        raise Oct24GPXSourceError("Non-increasing/naive GPX source time")
    return {"raw_points":len(points),
            "first_time_utc":times[0],
            "last_time_utc":times[-1],
            "source_size_bytes":len(data),
            "source_sha256":digest(data)}

def restore_second_gpx(root: Path, metadata: dict) -> bytes:
    segments = metadata.get("parts", [])
    if len(segments) != 21:
        raise Oct24GPXSourceError("Expected all 21 byte-exact source fragments")
    observed = []
    line_cursor = 1
    for index,entry in enumerate(segments):
        expected = (SOURCE_ROOT / "2026-10-24-0834_original.gpx.parts" /
                    f"part_{index:03d}.txt")
        if Path(entry["path"]) != expected or entry["line_start"] != line_cursor:
            raise Oct24GPXSourceError("Out-of-order or unexpected original GPX fragment")
        try:
            data = (root / expected).read_bytes()
        except FileNotFoundError as exc:
            raise Oct24GPXSourceError("Missing original GPX fragment: "+expected.as_posix()) from exc
        if (len(data) != entry["size_bytes"] or
                digest(data) != entry["sha256"] or
                git_blob_sha1(data) != entry["git_blob_sha1"]):
            raise Oct24GPXSourceError("GPX fragment digest/length mismatch: "+expected.as_posix()+f" len={len(data)}/{entry['size_bytes']} sha256={digest(data)}/{entry['sha256']} git_sha={git_blob_sha1(data)}/{entry['git_blob_sha1']}")
        lines = data.splitlines(keepends=True)
        if len(lines) != entry["line_end"] - entry["line_start"] + 1:
            raise Oct24GPXSourceError("GPX fragment line count mismatch")
        if index != len(segments)-1 and not data.endswith(b"\n"):
            raise Oct24GPXSourceError("Missing original source separator at fragment boundary")
        observed.append(data)
        line_cursor = entry["line_end"] + 1
    if line_cursor != metadata["original_utf8_lines"] + 1:
        raise Oct24GPXSourceError("Total source line count mismatch")
    return b"".join(observed)

def verify(root: Path=ROOT) -> dict:
    root = Path(root)
    manifest_path=root/SOURCE_ROOT/"source_manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version")!="habu-2026-10-24-original-gpx-exact-split-v1":
        raise Oct24GPXSourceError("Unexpected original-source archival schema")
    if manifest.get("raw_status")!="INCOMING_ONLY_NOT_CANONICAL_OR_SCIENTIFIC_EXPOSURE":
        raise Oct24GPXSourceError("Original incoming GPX must not become certified effort by import")
    refs=manifest.get("source_gpx_files")
    if not isinstance(refs,list) or len(refs)!=2:
        raise Oct24GPXSourceError("Exactly two original GPX references required")
    first_path=SOURCE_ROOT/"2026-10-24-0723_original.gpx"
    if refs[0].get("path")!=first_path.as_posix():
        raise Oct24GPXSourceError("Original first GPX storage path changed")
    try:
        first=(root/first_path).read_bytes()
    except FileNotFoundError as exc:
        raise Oct24GPXSourceError("Original first GPX source missing") from exc
    if git_blob_sha1(first)!=refs[0]["git_blob_sha1"]:
        raise Oct24GPXSourceError("Original first GPX Git object changed")
    second=restore_second_gpx(root,refs[1])
    a=verify_gpx(first,refs[0])
    b=verify_gpx(second,refs[1])
    first_end=datetime.fromisoformat(a["last_time_utc"].replace("Z","+00:00"))
    second_start=datetime.fromisoformat(b["first_time_utc"].replace("Z","+00:00"))
    gap=(second_start-first_end).total_seconds()
    actual_gap_ms=int(round(gap*1000))
    if actual_gap_ms!=4054000 or manifest.get("gap",{}).get("gap_seconds")!=4054:
        raise Oct24GPXSourceError("Observed 67m34s source GPS gap changed")
    if manifest["gap"].get("no_interpolation") is not True:
        raise Oct24GPXSourceError("Source GPS gap must remain missing")
    scope=manifest.get("registration",{})
    if (scope.get("science_negative_eligible")!=0 or
            scope.get("science_positive_eligible")!=0 or
            scope.get("original_p0_missing") is not True or
            scope.get("raw_status") == "CERTIFIED_SEARCH"):
        raise Oct24GPXSourceError("Unauthorized scientific label/P0 promotion")
    return {"status":"EXACT_ORIGINAL_TWO_GPXS_PRESERVED_IN_INCOMING",
            "operational_night":"2026-10-24",
            "first":a,"second":b,
            "total_original_gpx_points":a["raw_points"]+b["raw_points"],
            "gpx_gap_seconds_rounded":round(gap,3),
            "new_scientific_negative_labels":0,
            "new_scientific_positive_labels":0,
            "original_p0_verified":False,
            "nightly_search_effort_certified":False}

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",type=Path,default=ROOT)
    parser.add_argument("--reconstitute-to",type=Path,
                        help="Write second original bytes after SHA verification; never defaults to data/raw")
    args=parser.parse_args()
    result=verify(args.repo_root)
    if args.reconstitute_to:
        safe=args.reconstitute_to.resolve()
        raw=(args.repo_root/"data/raw").resolve()
        if safe==raw or raw in safe.parents:
            raise Oct24GPXSourceError("Do not auto-promote reconstructed source into canonical raw")
        content=restore_second_gpx(args.repo_root,
            json.loads((args.repo_root/SOURCE_ROOT/"source_manifest.json").read_text())["source_gpx_files"][1])
        if safe.exists():
            raise Oct24GPXSourceError("Refusing to overwrite an existing reconstructed GPX")
        safe.parent.mkdir(parents=True,exist_ok=True)
        safe.write_bytes(content)
        if digest(safe.read_bytes())!=result["second"]["source_sha256"]:
            raise Oct24GPXSourceError("Written reconstruction failed integrity check")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    sys.exit(main())
