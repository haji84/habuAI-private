#!/usr/bin/env python3
"""Build a bounded, prospective auxiliary road universe from the verified OSM archive.

No historical GPX, capture outcome or post-cutoff observation is read. The output
is INPUT CANDIDATE evidence, never production issuance or a frozen prediction.
"""
from __future__ import annotations

import argparse
import base64
import csv
import fcntl
import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
PARTS_RELATIVE = "artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts"
ARCHIVE_SHA256 = "f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17"
CELLS_SHA256 = "33ea1df38351d9c2454bf2efc9b00432119e484d5d549a567bc8fd2d337151a4"
CELLS_SUFFIX = "04_processed_road/osm_road_candidate_cells.csv"
EXPECTED_CELLS = 16990
MAX_WINDOWS_PER_SHARD = 6
REQUIRED_PARTS = 33
FEATURE_NAMES = ("road_axial_cos", "road_axial_sin", "road_length_m")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def aware(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timezone-aware timestamps are required")
    return parsed


def operational_night(value):
    return (value.astimezone(JST) - timedelta(hours=7)).date().isoformat()


def load_verified_road_csv(repo_root):
    """Restore and attest original archive *in memory*, without executing ZIP code."""
    base = Path(repo_root) / PARTS_RELATIVE
    if not base.is_dir():
        raise ValueError("Missing original OSM ZIP parts")
    names = sorted(p.name for p in base.iterdir() if p.name.startswith("part_"))
    expected = [f"part_{i:03d}.b64" for i in range(REQUIRED_PARTS)]
    if names != expected:
        raise ValueError("Missing, duplicate or unexpected OSM archive part")
    raw_parts = []
    for name in expected:
        file = base / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 200001:
            raise ValueError("Invalid archive part")
        raw_parts.append(file.read_bytes())
    if sum(map(len, raw_parts)) > 7_000_000:
        raise ValueError("Archive base64 size limit exceeded")
    zipped = base64.b64decode(b"".join(raw_parts), validate=True)
    if len(zipped) > 5_000_000 or digest(zipped) != ARCHIVE_SHA256:
        raise ValueError("Original OSM archive SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
        infos = archive.infolist()
        if len(infos) > 10000 or sum(x.file_size for x in infos) > 300_000_000:
            raise ValueError("OSM archive expansion limit exceeded")
        names = set()
        candidate = []
        for entry in infos:
            name = entry.filename
            parts = Path(name).parts
            if (name.startswith("/") or "\\" in name or ":" in name or
                not parts or ".." in parts or name in names or
                entry.flag_bits & 1 or entry.file_size > 100_000_000 or
                (entry.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("Unsafe OSM archive entry")
            names.add(name)
            if name == CELLS_SUFFIX or name.endswith("/" + CELLS_SUFFIX):
                candidate.append(entry)
        if len(candidate) != 1:
            raise ValueError("Exact OSM road CSV not found once")
        entry = candidate[0]
        if entry.file_size != 4408826:
            raise ValueError("Unexpected original road CSV length")
        raw = archive.read(entry)
        if digest(raw) != CELLS_SHA256:
            raise ValueError("Road CSV SHA-256 mismatch")
    return raw


def parse_road_cells(csv_bytes, *, expected_cells=EXPECTED_CELLS):
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    required = {"cell_id", "cell_x_index", "cell_y_index", "cell_center_x",
                "cell_center_y", "normal_route", "road_length_m",
                "road_direction_deg", "candidate_source", "island_name"}
    if not reader.fieldnames or not required <= set(reader.fieldnames):
        raise ValueError("Incomplete OSM road cell CSV columns")
    output, seen = [], set()
    for row in reader:
        try:
            xcell = int(row["cell_x_index"])
            ycell = int(row["cell_y_index"])
            x = float(row["cell_center_x"])
            y = float(row["cell_center_y"])
            length = float(row["road_length_m"])
            angle = float(row["road_direction_deg"])
        except (ValueError, TypeError) as error:
            raise ValueError("Invalid OSM road numeric field") from error
        identity = (xcell, ycell)
        if (identity in seen or row["cell_id"] != f"utm52n_100m_{xcell}_{ycell}" or
            not 100000 <= x <= 900000 or not 0 <= y <= 10000000 or
            abs(x - (xcell * 100 + 50)) > 0.01 or
            abs(y - (ycell * 100 + 50)) > 0.01 or
            not math.isfinite(length) or length <= 0 or
            not math.isfinite(angle) or not 0 <= angle < 180 or
            row["normal_route"].lower() not in {"true", "1"} or
            row["candidate_source"] != "osm_auxiliary" or
            row["island_name"] not in {"奄美大島", "加計呂麻島"}):
            raise ValueError("Invalid, restricted or duplicate road cell")
        seen.add(identity)
        output.append({"cell_id": row["cell_id"], "x": x, "y": y,
                       "island": row["island_name"], "length": length, "direction": angle})
        if len(output) > expected_cells:
            raise ValueError("Road cell count exceeded")
    if len(output) != expected_cells:
        raise ValueError("Incomplete verified road cell universe")
    return sorted(output, key=lambda v: v["cell_id"])


def build_artifacts(cells, night, cutoff, first_window, window_count, available_at):
    """Build one limited, full-spatial-coverage future shard; no capture labels."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", night):
        raise ValueError("Invalid operational night")
    if not isinstance(window_count, int) or isinstance(window_count, bool) or not 1 <= window_count <= MAX_WINDOWS_PER_SHARD:
        raise ValueError("Invalid shard size")
    cutoff, first_window, available_at = map(aware, (cutoff, first_window, available_at))
    if (operational_night(cutoff) != night or available_at >= cutoff or
        first_window <= cutoff):
        raise ValueError("Source readiness/cutoff/window order invalid")
    start = first_window.astimezone(JST)
    if start.minute % 10 or start.second or start.microsecond:
        raise ValueError("Window must align to ten-minute bins")
    times = [start + timedelta(minutes=10 * i) for i in range(window_count)]
    if any(operational_night(t) != night for t in times):
        raise ValueError("Forecast window crosses the operational-night boundary")
    rows = []
    values = {name: {} for name in FEATURE_NAMES}
    for t in times:
        iso = t.isoformat()
        suffix = t.strftime("%Y%m%dT%H%M%z")
        for cell in cells:
            rowid = cell["cell_id"] + "@" + suffix
            rows.append({"row_id": rowid, "operational_night": night,
                         "cutoff_time": cutoff.isoformat(),
                         "window_start_jst": iso,
                         "utm_x_m": cell["x"], "utm_y_m": cell["y"]})
            radians = math.radians(2 * cell["direction"])
            values["road_axial_cos"][rowid] = math.cos(radians)
            values["road_axial_sin"][rowid] = math.sin(radians)
            values["road_length_m"][rowid] = cell["length"]
    universe = {
        "schema_version": "1.0", "source_type": "EX_ANTE_FORECAST",
        "geographic_domain": {
            "islands": ["奄美大島", "加計呂麻島"],
            "crs": "EPSG:32652",
            "source_class": "osm_auxiliary",
            "archive_sha256": ARCHIVE_SHA256,
            "road_cells_csv_sha256": CELLS_SHA256,
            "planning_scope": "up_to_six_ten_minute_windows_only",
            "official_road_eligibility": "NOT_VALIDATED",
            "legal_access_and_current_closures": "UNKNOWN",
        },
        "rows": rows,
    }
    features = []
    for name in FEATURE_NAMES:
        features.append({
            "schema_version": "1.0", "feature_name": name, "use_role": "static_predictor",
            "operational_night": night, "cutoff_time": cutoff.isoformat(),
            "available_at": available_at.isoformat(), "values": values[name],
            "source_class": "osm_auxiliary",
        })
    return universe, features


def materialize(repo_root, output_root, night, cutoff, first_window, window_count):
    """Output to a new derived workspace only; never modify canonical raw/ORIGINAL."""
    csv_bytes = load_verified_road_csv(repo_root)
    cells = parse_road_cells(csv_bytes)
    created = datetime.now(timezone.utc)
    universe, features = build_artifacts(cells, night, cutoff, first_window,
                                         window_count, created.isoformat())
    output_root = Path(output_root).absolute()
    output_root.mkdir(parents=True, exist_ok=True)
    ref = f"features/forecast_builds/{night}/{created.strftime('%Y%m%dT%H%M%S%fZ')}"
    parent = output_root / "features" / "forecast_builds" / night
    parent.mkdir(parents=True, exist_ok=True)
    destination = output_root / ref
    lock_file = parent / ".materialization.lock"
    with lock_file.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if destination.exists():
            raise ValueError("Forecast shard already exists")
        with tempfile.TemporaryDirectory(prefix=".forecast-pending-", dir=parent) as scratch:
            temp = Path(scratch)
            urel = ref + "/universe.json"
            ubytes = canonical(universe) + b"\n"
            (temp / "universe.json").write_bytes(ubytes)
            feature_refs = []
            for feature in features:
                relative = ref + "/" + feature["feature_name"] + ".json"
                encoded = canonical(feature) + b"\n"
                (temp / (feature["feature_name"] + ".json")).write_bytes(encoded)
                feature_refs.append({"path": relative, "sha256": digest(encoded),
                                     "available_at": created.isoformat()})
            snapshot = {
                "schema_version": "2.0", "operational_night": night,
                "cutoff_time": aware(cutoff).isoformat(),
                "universe": {"path": urel, "sha256": digest(ubytes),
                             "available_at": created.isoformat()},
                "features": feature_refs,
                "feature_schema_sha256": digest(canonical(sorted(FEATURE_NAMES))),
                "qualification": "AUXILIARY_ROADS_INPUT_ONLY_NOT_OFFICIAL",
            }
            (temp / "snapshot.json").write_bytes(canonical(snapshot) + b"\n")
            for file in temp.iterdir():
                if file.is_file():
                    with file.open("rb") as stream:
                        os.fsync(stream.fileno())
            os.rename(temp, destination)
    return {
        "status": "PREPRODUCTION_INPUT_ONLY",
        "official_prediction_eligible": False,
        "snapshot": ref + "/snapshot.json",
        "snapshot_sha256": digest((destination / "snapshot.json").read_bytes()),
        "rows": len(universe["rows"]),
        "cells": len(cells),
        "windows": window_count,
        "missing_for_official_prediction": [
            "TRUSTED_SOURCE_AVAILABILITY_RECEIPT", "WEATHER_AND_ENVIRONMENT",
            "DEM_TERRAIN_WIND", "MODEL_CHAMPION", "FORMAL_TARGETS",
            "FULL_NIGHT_UNIVERSE", "ROUTE_OPTIMIZER", "TASK8_TRUSTED_ISSUANCE",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--night", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--first-window", required=True)
    parser.add_argument("--windows", type=int, default=1)
    args = parser.parse_args()
    result = materialize(args.repo_root, args.output_root, args.night,
                         args.cutoff, args.first_window, args.windows)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
