#!/usr/bin/env python3
"""Build a bounded, prospective auxiliary road universe from the verified OSM archive.

No historical GPX, capture outcome or post-cutoff observation is read. The output
is INPUT CANDIDATE evidence, never production issuance or a frozen prediction.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from master_contracts import safe_path

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
    repo_root = Path(repo_root).resolve(strict=True)
    output_root = Path(output_root).absolute()
    # Check the lexical path before resolving it, including existing ancestors.
    output_root = safe_path(Path(output_root.anchor), str(output_root.relative_to(output_root.anchor)))
    if output_root == repo_root or output_root.is_relative_to(repo_root):
        raise ValueError("Derived forecast output must be outside the canonical repository")
    # Pure parsing/building is portable. Durable publication still requires the
    # real POSIX lock and directory-fsync implementation, before any byte write.
    import fcntl
    csv_bytes = load_verified_road_csv(repo_root)
    cells = parse_road_cells(csv_bytes)
    created = datetime.now(timezone.utc)
    universe, features = build_artifacts(cells, night, cutoff, first_window,
                                         window_count, created.isoformat())
    output_root.mkdir(parents=True, exist_ok=True)
    ref = f"features/forecast_builds/{night}/{created.strftime('%Y%m%dT%H%M%S%fZ')}"
    parent = safe_path(output_root, f"features/forecast_builds/{night}")
    destination = safe_path(output_root, ref)
    lock_file = safe_path(output_root, f"features/forecast_builds/{night}/.materialization.lock")
    if any(path.resolve().is_relative_to(repo_root) for path in (parent, destination, lock_file)):
        raise ValueError("Derived forecast output must be outside the canonical repository")
    parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(lock_file, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), "a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        safe_path(output_root, ref)
        if destination.exists():
            raise ValueError("Forecast shard already exists")
        published = False
        cutoff_time = aware(cutoff)
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
                feature_refs.append({"path": relative, "sha256": digest(encoded)})
            for file in temp.iterdir():
                if file.is_file():
                    with file.open("rb") as stream:
                        os.fsync(stream.fileno())
            _sync_directory(temp)
            try:
                safe_path(output_root, ref)
                os.rename(temp, destination)
                published = True
                _sync_directory(parent)
                source_ready = datetime.now(timezone.utc)
                if source_ready >= cutoff_time:
                    raise ValueError("Materialization completed at or after cutoff")
                for reference in feature_refs:
                    reference["available_at"] = source_ready.isoformat()
                snapshot = {
                    "schema_version": "2.0", "operational_night": night,
                    "cutoff_time": cutoff_time.isoformat(),
                    "universe": {"path": urel, "sha256": digest(ubytes),
                                 "available_at": source_ready.isoformat()},
                    "features": feature_refs,
                    "feature_schema_sha256": digest(canonical(sorted(FEATURE_NAMES))),
                    "qualification": "AUXILIARY_ROADS_INPUT_ONLY_NOT_OFFICIAL",
                }
                snapshot_bytes = canonical(snapshot) + b"\n"
                pending_snapshot = safe_path(output_root, ref + "/.snapshot-pending")
                with pending_snapshot.open("xb") as stream:
                    stream.write(snapshot_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                safe_path(output_root, ref + "/snapshot.json")
                os.rename(pending_snapshot, destination / "snapshot.json")
                _sync_directory(destination)
                completed = datetime.now(timezone.utc)
                if completed >= cutoff_time:
                    raise ValueError("Materialization completed at or after cutoff")
            except BaseException:
                if published:
                    # Only this call's new shard is removable; existing output is immutable.
                    shutil.rmtree(safe_path(output_root, ref))
                    _sync_directory(parent)
                raise
    return {
        "status": "PREPRODUCTION_INPUT_ONLY",
        "official_prediction_eligible": False,
        "snapshot": ref + "/snapshot.json",
        "snapshot_sha256": digest(snapshot_bytes),
        "completed_at": completed.isoformat(),
        "rows": len(universe["rows"]),
        "cells": len(cells),
        "windows": window_count,
        "missing_for_official_prediction": [
            "TRUSTED_SOURCE_AVAILABILITY_RECEIPT", "WEATHER_AND_ENVIRONMENT",
            "DEM_TERRAIN_WIND", "MODEL_CHAMPION", "FORMAL_TARGETS",
            "FULL_NIGHT_UNIVERSE", "ROUTE_OPTIMIZER", "TASK8_TRUSTED_ISSUANCE",
        ],
    }


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _git_head(root, context):
    context.check()
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, check=True,
                            capture_output=True, text=True, timeout=context.remaining_seconds)
    context.check()
    sha = result.stdout.strip()
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise ValueError('Current source Git commit identity required')
    return sha


class _G0CapsuleWriter:
    """Exclusive, guarded current-run writes with real fsync/hash/readback."""
    def __init__(self, root, context, cutoff):
        import g0_forecast_contract as g0
        self.root, self.context, self.cutoff = root, context, cutoff
        self.reader = g0.G0ArtifactReader(root, context)
        self.last = None

    def now(self):
        self.context.check()
        stamp = datetime.now(timezone.utc)
        if stamp >= self.cutoff or (self.last is not None and stamp < self.last):
            raise ValueError('G0_INPUT_BLOCKED: current-run completion must precede cutoff without backdating')
        self.last = stamp
        return stamp.isoformat()

    def path(self, relative):
        import prospective_inputs as pi
        return pi._local_path(self.root, relative, self.context.check)

    def sync_directory(self, path):
        self.context.check()
        # File fsync and atomic publication are real on both platforms. Windows
        # cannot claim the separate POSIX directory durability barrier.
        if os.name == 'posix':
            _sync_directory(path)
        self.context.check()

    def write(self, relative, raw, *, received_at=None, small=False):
        import g0_forecast_contract as g0
        self.context.check()
        received = received_at or self.now()
        ref = dict(path=relative, sha256=digest(raw), size_bytes=len(raw))
        if len(raw) > (g0.MAX_SMALL_BYTES if small else 128 * 1024**2):
            raise g0.ForecastCapacityError('CAPACITY_BLOCKED: generated source bytes')
        derived = self.now()
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = self.path(relative)
        with target.open('xb') as stream:
            if stream.write(raw) != len(raw):
                raise OSError('Incomplete derived artifact write')
            stream.flush()
            os.fsync(stream.fileno())
        self.sync_directory(target.parent)
        materialized = self.now()
        if self.reader.read(ref, small=small, parse=False) != raw:
            raise ValueError('Derived artifact readback mismatch')
        audited = self.now()
        readiness = dict(source_received_at=received, derived_at=derived,
                         materialized_at=materialized, audited_at=audited)
        return dict(ref, readiness=readiness, usable_at=audited)

    def json(self, relative, value, *, small=False):
        self.context.check()
        raw = canonical(value) + b'\n'
        self.context.check()
        return self.write(relative, raw, small=small)


def _g0_node(identifier, kind, role, parents, bound, valid):
    return dict(id=identifier, source_kind=kind, role=role, parents=parents,
                ref={key: bound[key] for key in ('path', 'sha256', 'size_bytes')},
                readiness=bound['readiness'], usable_at=bound['usable_at'],
                event_time=None, valid_time=valid, allowed_use='FORECAST_INPUT', source_class='auxiliary')


def _g0_shard(writer, cells, first, start_index, stop_index, night, cutoff, nodes):
    """One bounded cell-major shard; never builds the full cell×night product."""
    import g0_forecast_contract as g0
    rows, values, physical = [], {name: {} for name in FEATURE_NAMES}, {}
    sid = f's{start_index:03d}'
    prefix = f'features/shards/{sid}'
    valid = dict(start=(first + timedelta(minutes=10 * start_index)).isoformat(),
                 end=(first + timedelta(minutes=10 * stop_index)).isoformat())
    for cell in cells:
        for ti in range(start_index, stop_index):
            writer.context.check()
            stamp = first + timedelta(minutes=10 * ti)
            rowid = f'{cell[0]}:{cell[1]}@{stamp.strftime("%Y-%m-%dT%H:%M:%SZ")}'
            rows.append(dict(row_id=rowid, operational_night=night, cutoff_time=cutoff.isoformat(),
                             window_start_jst=stamp.isoformat(), utm_x_m=cell[0] * 100 + 50,
                             utm_y_m=cell[1] * 100 + 50))
            for name in FEATURE_NAMES:
                values[name][rowid] = cells[cell][name]
            physical[rowid] = {name: dict(start=stamp.isoformat(), end=(stamp + timedelta(minutes=10)).isoformat())
                               for name in FEATURE_NAMES}
    u = writer.json(prefix + '-u.json', dict(schema_version='1.0', source_type='EX_ANTE_FORECAST',
                   geographic_domain={'crs': 'EPSG:32652', 'name': 'ARCHIVED_AUXILIARY_OSM_CELLS_NOT_CURRENT_ROAD_ACCESS'}, rows=rows))
    unode = _g0_node(sid + '-u', 'forecast_universe', 'universe', ['domain'], u, valid)
    nodes.append(unode)
    features, fids = [], []
    for name in FEATURE_NAMES:
        writer.context.check()
        # Payload availability is the time these values exist in memory; the
        # reference/node carries their later observed persisted/readback time.
        available = writer.now()
        f = writer.json(prefix + '-' + name + '.json', dict(schema_version='1.0', feature_name=name,
                        use_role='static_predictor', operational_night=night, cutoff_time=cutoff.isoformat(),
                        available_at=available, values=values[name]))
        fid = sid + '-' + name
        nodes.append(_g0_node(fid, 'feature_values', 'feature', ['projection-' + name], f, valid))
        features.append({key: f[key] for key in ('path', 'sha256', 'size_bytes')})
        features[-1]['available_at'] = f['usable_at']
        fids.append(fid)
    validity = writer.json(prefix + '-v.json', dict(schema_version='habu-g0-validity-v1',
                           feature_sources={name: [sid + '-' + name] for name in FEATURE_NAMES}, rows=physical))
    nodes.append(_g0_node(sid + '-v', 'validity', 'protocol', fids, validity, valid))
    snapshot = writer.json(prefix + '-s.json', dict(schema_version='2.0', operational_night=night,
                           cutoff_time=cutoff.isoformat(), universe=dict(unode['ref'], available_at=u['usable_at']),
                           features=features, feature_schema_sha256=digest(canonical(sorted(FEATURE_NAMES)))))
    nodes.append(_g0_node(sid + '-s', 'snapshot', 'protocol', [unode['id'], *fids], snapshot, valid))
    return dict(shard_id=sid, cell_partition=0, time_partition=start_index, snapshot_id=sid + '-s', validity_id=sid + '-v')


def materialize_g0(repo_root, output_root, night, cutoff, first_window, window_count,
                   *, budget_seconds=300, _read_context=None):
    """Create a new auxiliary capsule, with future-cutoff software rehearsal only.

    All current-run reads, readbacks, archive expansion and full-set validation
    share one deadline/actual-byte ledger. No success or public output is exposed
    before all shards and final rescans pass. Actual issuance must revalidate at
    its real clock; this API cannot grant model, fit or production authority.
    """
    import g0_forecast_contract as g0
    import prospective_inputs as pi
    context = _read_context
    if context is None:
        context = pi.ProspectiveReadContext(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
    elif isinstance(context, pi.ProspectiveReadContext):
        context.restrict(budget_seconds, g0.MAX_TOTAL_READ_BYTES)
    else:
        raise ValueError('Invalid shared read context')
    initial_bytes = context.bytes_read
    context.check()
    repo_root, output_root = Path(repo_root).absolute(), Path(output_root).absolute()
    repo_root = pi._local_path(repo_root, '', context.check)
    output_root = pi._local_path(output_root, '', context.check)
    if output_root == repo_root or output_root.is_relative_to(repo_root):
        raise ValueError('Derived capsule must be outside the canonical repository')
    if output_root.exists():
        raise ValueError('Derived capsule output must not already exist')
    cutoff, first = aware(cutoff).astimezone(timezone.utc), aware(first_window).astimezone(timezone.utc)
    if (isinstance(window_count, bool) or not isinstance(window_count, int) or not 1 <= window_count <= g0.MAX_WINDOWS):
        raise ValueError('Invalid whole-domain window count')
    last = first + timedelta(minutes=10 * window_count)
    g0._horizon(dict(start=first.isoformat(), end=last.isoformat()), night, cutoff)
    if operational_night(cutoff) != night:
        raise ValueError('Cutoff operational-night mismatch')
    if datetime.now(timezone.utc) >= cutoff:
        raise ValueError('G0_INPUT_BLOCKED: actual intake is at or after cutoff')
    source_sha = _git_head(repo_root, context)
    source_reader = g0.G0ArtifactReader(repo_root, context)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    pi._local_path(output_root, '', context.check)
    published = False
    with tempfile.TemporaryDirectory(prefix='.g0-osm-pending-', dir=output_root.parent) as folder:
        staging = Path(folder).absolute()
        identity = staging.stat()
        writer = _G0CapsuleWriter(staging, context, cutoff)
        started = writer.now()

        def original(relative, maximum):
            context.check()
            path = pi._local_path(repo_root, relative, context.check)
            raw = pi._bounded_bytes(path, pi._LocalByteBudget(context, maximum), context.check)
            ref = dict(path=relative, sha256=digest(raw), size_bytes=len(raw))
            context.check()
            # The discover/read pass and the bound source reread are both billed.
            if source_reader.read(ref, parse=False) != raw:
                raise ValueError('Original source changed during intake')
            received = writer.now()
            return raw, received

        nodes, parts, encoded = [], [], []
        for index in range(33):
            relative = f'{g0.OSM_PARTS_PATH}/part_{index:03d}.b64'
            raw, received = original(relative, g0.OSM_PART_CHUNK_BYTES + 1)
            b = writer.write(relative, raw, received_at=received)
            node = _g0_node(f'part-{index:03d}', 'osm_archive_part', 'protocol', [], b, None)
            nodes.append(node)
            parts.append({key: node[key] for key in ('id', 'ref', 'readiness', 'usable_at')})
            encoded.append(raw)
        completed_parts = writer.now()
        csv_raw = g0.decode_osm_road_archive(b''.join(encoded), context)
        cells = dict(sorted(g0.parse_osm_road_csv(csv_raw, check=context.check).items()))
        if len(cells) * window_count > g0.MAX_DOMAIN_ROWS:
            raise g0.ForecastCapacityError('CAPACITY_BLOCKED: declared domain rows')
        if len(cells) * len(FEATURE_NAMES) > pi.MAX_JOIN_CELLS:
            raise g0.ForecastCapacityError('CAPACITY_BLOCKED: per-shard joined numeric cells')
        csv_ref = writer.write('data/processed/osm/cells.csv', csv_raw)
        proof = writer.json('features/osm-current-intake.json', dict(schema_version='habu-g0-osm-current-intake-v1',
                            purpose='CURRENT_RUN_BYTE_EXACT_REINGESTION', source_git_sha=source_sha,
                            started_at=started, parts_completed_at=completed_parts, parts=parts,
                            archive_sha256=g0.OSM_ARCHIVE_SHA256, archive_size_bytes=g0.OSM_ARCHIVE_BYTES,
                            member_path=g0.OSM_CSV_MEMBER, csv_sha256=g0.OSM_CSV_SHA256, csv_size_bytes=g0.OSM_CSV_BYTES,
                            historical_access='NOT_ATTESTED', source_authenticity='NOT_ATTESTED'), small=True)
        # CSV's closure audit includes the now-materialized proof reference.
        writer.reader.read({key: csv_ref[key] for key in g0.REF_FIELDS}, parse=False)
        csv_ref['readiness']['audited_at'] = csv_ref['usable_at'] = writer.now()
        csv_node = _g0_node('osm-csv', 'osm_road_cells_csv', 'protocol', [p['id'] for p in parts], csv_ref, None)
        csv_node['provenance_ref'] = proof
        nodes.append(csv_node)
        policy_raw, received = original(g0.POLICY_PATH, g0.MAX_SMALL_BYTES)
        policy_ref = writer.write(g0.POLICY_PATH, policy_raw, received_at=received, small=True)
        code_path = 'scripts/build_osm_prospective_universe.py'
        code_raw, received = original(code_path, pi.MAX_SOURCE_BYTES)
        code_ref = writer.write(code_path, code_raw, received_at=received)
        valid = dict(start=first.isoformat(), end=last.isoformat())
        for operation in ('candidate_cells', *FEATURE_NAMES):
            b = writer.json('features/projection-' + operation + '.json',
                            dict(schema_version='habu-g0-osm-static-projection-v1', version='1', operation=operation,
                                 source_csv_node_id='osm-csv', code_ref=code_ref))
            nodes.append(_g0_node('projection-' + operation, 'osm_static_projection',
                                 'universe' if operation == 'candidate_cells' else 'feature', ['osm-csv'], b, valid))
        domain = writer.json('features/domain.json', dict(schema_version='habu-g0-cell-domain-v1', crs='EPSG:32652',
                             source_class='auxiliary', required_source_ids=['projection-candidate_cells'],
                             cells=[list(cell) for cell in cells]), small=True)
        nodes.append(_g0_node('domain', 'cell_domain', 'universe', ['projection-candidate_cells'], domain, valid))
        features = []
        for name in FEATURE_NAMES:
            text = {'road_length_m': 'Archived auxiliary OSM processed road length in the 100m cell',
                    'road_axial_cos': 'Cosine of twice the archived auxiliary OSM road axis angle',
                    'road_axial_sin': 'Sine of twice the archived auxiliary OSM road axis angle'}[name]
            features.append(dict(name=name, units=g0.OSM_FEATURE_UNITS[name], version='1', definition=text,
                                 definition_sha256=digest(text.encode()), code_ref=code_ref, deployment='static_predictor',
                                 required_source_ids=['projection-' + name]))
        definition_sha = digest(canonical(sorted([dict(f, code_ref={key: code_ref[key] for key in g0.REF_FIELDS})
                                                  for f in features], key=lambda item: item['name'])))
        shards = [_g0_shard(writer, cells, first, i, i + 1, night, cutoff, nodes) for i in range(window_count)]
        own = writer.now()
        manifest = dict(schema_version=g0.SCHEMA, operational_night=night, cutoff_time=cutoff.isoformat(),
                        readiness={key: own for key in pi.READINESS_FIELDS}, usable_at=own, policy_ref=policy_ref,
                        domain_id='domain', source_nodes=nodes, features=features, feature_definition_sha256=definition_sha,
                        horizon=valid, cell_partitions=[[0, len(cells)]], time_partitions=[[i, i + 1] for i in range(window_count)],
                        shards=shards)
        manifest_bound = writer.json('features/g0-contract.json', manifest, small=True)
        manifest_ref = {key: manifest_bound[key] for key in g0.REF_FIELDS}
        # This is explicitly a declaration rehearsal at a future cutoff, never
        # a false claim that the actual issuance clock has reached that cutoff.
        validation = g0.validate_g0_forecast(staging, manifest_ref, night, cutoff,
                                            expected_feature_definition_sha256=definition_sha,
                                            budget_seconds=budget_seconds, _read_context=context)
        source_reader.rescan()
        writer.now()
        pi._local_path(output_root, '', context.check)
        pi._local_path(staging, '', context.check)
        if output_root.exists():
            raise ValueError('Derived capsule destination appeared during construction')
        try:
            os.rename(staging, output_root)
            published = True
            writer.sync_directory(output_root.parent)
            completed = writer.now()
            pi._local_path(output_root, '', context.check)
            if (output_root.stat().st_dev, output_root.stat().st_ino) != (identity.st_dev, identity.st_ino):
                raise ValueError('Published capsule directory identity changed')
            result = dict(status='AUXILIARY_G0_SOFTWARE_REHEARSAL_ONLY', manifest_ref=manifest_ref,
                          feature_definition_sha256=definition_sha, rows=len(cells) * window_count,
                          cells=len(cells), windows=window_count, shards=len(shards), actual_completed_at=completed,
                          validation_clock='DECLARED_FUTURE_CUTOFF_REHEARSAL', actual_issuance_revalidation_required=True,
                          publication_durability='POSIX_DIRECTORY_FSYNC' if os.name == 'posix' else 'FILE_FSYNC_ATOMIC_RENAME_ONLY',
                          historical_access='NOT_ATTESTED', source_authenticity='NOT_ATTESTED',
                          coverage='DECLARED_ARCHIVED_OSM_CELLS_ONLY', current_road_access='NOT_ATTESTED',
                          model_collection='NOT_RUN_SEPARATE_120000_ROWS_AND_16MIB_GATE', validation=validation,
                          actual_read_bytes=context.bytes_read, producer_read_bytes=context.bytes_read - initial_bytes,
                          issuance_authorized=False, fit_authorized=False, scientific_execution_authorized=False,
                          production_authorized=False)
            writer.now()
            context.check()
            return result
        except BaseException:
            if published:
                # Only this call's new, guarded directory with the same file ID
                # can be removed; never follow a replacement reparse/symlink.
                # Cleanup cannot require an unexpired validation deadline. It
                # still uses the full reparse/containment guard and file ID.
                checked = pi._local_path(output_root, '', lambda: None)
                if (checked.stat().st_dev, checked.stat().st_ino) == (identity.st_dev, identity.st_ino):
                    shutil.rmtree(checked)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--night", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--first-window", required=True)
    parser.add_argument("--windows", type=int, default=1)
    parser.add_argument("--strict-g0", action="store_true", help="Additive complete declared-horizon software rehearsal capsule")
    parser.add_argument("--budget-seconds", type=float, default=300, help="Shared strict-G0 elapsed cap (at most 300s)")
    args = parser.parse_args()
    if args.strict_g0:
        result = materialize_g0(args.repo_root, args.output_root, args.night,
                                args.cutoff, args.first_window, args.windows, budget_seconds=args.budget_seconds)
    else:
        result = materialize(args.repo_root, args.output_root, args.night,
                             args.cutoff, args.first_window, args.windows)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

