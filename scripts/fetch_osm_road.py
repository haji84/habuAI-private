from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.osm_road import (  # noqa: E402
    aggregate_road_cells,
    build_bbox_tiles,
    classify_vehicle_route,
    clip_parts_to_target,
    deduplicate_elements,
    load_target_polygons,
    parse_overpass_elements,
    partition_tiles_by_target_polygon,
    point_in_multipolygon,
    prepare_polygons,
    reconstruct_way_parts,
)
from src.public_data import AMAMI_MAIN_ISLAND_BBOX  # noqa: E402


DEFAULT_OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
BOUNDARY_URL = (
    "https://nominatim.openstreetmap.org/lookup?"
    "osm_ids=R4098976,R4098962&format=geojson&polygon_geojson=1"
)
TARGET_RELATION_IDS = {4098976, 4098962}
TARGET_RELATION_NAMES = {4098976: "奄美大島", 4098962: "加計呂麻島"}
ATTRIBUTION = "© OpenStreetMap contributors; ODbL 1.0"
USER_AGENT = "HabuAI-OSM-road-audit/1.0 (non-commercial research)"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_overpass_query(bbox_south_west_north_east: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox_south_west_north_east
    return (
        '[out:json][timeout:120];way["highway"]'
        f"({south:.7f},{west:.7f},{north:.7f},{east:.7f});"
        "out body;>;out skel qt;"
    )


def fetch_url(url: str, timeout: int = 180) -> tuple[int, bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read(), str(response.geturl())
    except HTTPError as exc:
        return int(exc.code), exc.read(), str(exc.geturl())


def _overpass_url(endpoint: str, query: str) -> str:
    return f"{endpoint}?{urlencode({'data': query})}"


def _payload_metadata(payload: bytes) -> tuple[str, int]:
    decoded = json.loads(payload)
    elements = decoded.get("elements")
    if not isinstance(elements, list):
        raise ValueError("response has no elements list")
    return str(decoded.get("osm3s", {}).get("timestamp_osm_base", "")), len(elements)


def acquire_tiles(
    tiles: list[dict],
    raw_root: Path,
    *,
    fetcher=fetch_url,
    endpoint: str = DEFAULT_OVERPASS_ENDPOINT,
    retry_attempts: int = 3,
    sleep_seconds: float = 1.0,
    request_timeout_seconds: int = 60,
) -> list[dict[str, object]]:
    raw_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for tile in tiles:
        tile_id = str(tile["tile_id"])
        bbox = tuple(tile["bbox_south_west_north_east"])
        query = build_overpass_query(bbox)
        url = _overpass_url(endpoint, query)
        destination = raw_root / f"{tile_id}.json"
        base = {
            "tile_id": tile_id,
            "bbox_south_west_north_east": json.dumps(bbox, separators=(",", ":")),
            "query": query,
            "endpoint": endpoint,
            "requested_url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "request_timeout_seconds": request_timeout_seconds,
        }
        if destination.exists():
            payload = destination.read_bytes()
            try:
                osm_base, element_count = _payload_metadata(payload)
                rows.append({
                    **base, "status": "cached", "http_status": 200,
                    "saved_path": str(destination), "bytes": len(payload),
                    "sha256": sha256_bytes(payload), "osm_base_timestamp": osm_base,
                    "element_count": element_count, "attempts": 0, "error": "",
                })
            except Exception as exc:
                rows.append({
                    **base, "status": "invalid_cached_raw", "http_status": "",
                    "saved_path": str(destination), "bytes": len(payload),
                    "sha256": sha256_bytes(payload), "osm_base_timestamp": "",
                    "element_count": 0, "attempts": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                })
            continue

        final_row = None
        for attempt in range(1, retry_attempts + 1):
            try:
                status, payload, final_url = fetcher(url, request_timeout_seconds)
                if status == 200:
                    osm_base, element_count = _payload_metadata(payload)
                    temporary = destination.with_suffix(".json.part")
                    temporary.write_bytes(payload)
                    temporary.replace(destination)
                    final_row = {
                        **base, "status": "downloaded", "http_status": status,
                        "final_url": final_url, "saved_path": str(destination),
                        "bytes": len(payload), "sha256": sha256_bytes(payload),
                        "osm_base_timestamp": osm_base, "element_count": element_count,
                        "attempts": attempt, "error": "",
                    }
                    break
                final_row = {
                    **base, "status": "http_error", "http_status": status,
                    "final_url": final_url, "saved_path": "", "bytes": len(payload),
                    "sha256": sha256_bytes(payload), "osm_base_timestamp": "",
                    "element_count": 0, "attempts": attempt,
                    "error": payload[:300].decode("utf-8", errors="replace"),
                }
            except Exception as exc:
                final_row = {
                    **base, "status": "request_error", "http_status": "",
                    "final_url": "", "saved_path": "", "bytes": 0,
                    "sha256": "", "osm_base_timestamp": "", "element_count": 0,
                    "attempts": attempt, "error": f"{type(exc).__name__}: {exc}",
                }
            if attempt < retry_attempts and sleep_seconds:
                time.sleep(sleep_seconds * attempt)
        rows.append(final_row or {**base, "status": "request_error", "error": "no attempt"})
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return rows


def subdivide_tile(tile: dict) -> list[dict[str, object]]:
    south, west, north, east = tuple(tile["bbox_south_west_north_east"])
    middle_lat = (south + north) / 2.0
    middle_lon = (west + east) / 2.0
    boxes = [
        (south, west, middle_lat, middle_lon),
        (south, middle_lon, middle_lat, east),
        (middle_lat, west, north, middle_lon),
        (middle_lat, middle_lon, north, east),
    ]
    return [
        {
            "tile_id": f'{tile["tile_id"]}_s{index:02d}',
            "bbox_south_west_north_east": tuple(round(value, 12) for value in bbox),
        }
        for index, bbox in enumerate(boxes)
    ]


def recover_unreferenced_raw_rows(
    raw_root: Path,
    existing_rows: list[dict],
    root_tiles: list[dict],
    endpoint: str,
) -> list[dict[str, object]]:
    known = {
        str(Path(str(row["saved_path"])).resolve())
        for row in existing_rows if row.get("saved_path")
    }
    roots = {str(tile["tile_id"]): tile for tile in root_tiles}
    recovered = []
    for path in sorted(raw_root.glob("*.json")):
        if str(path.resolve()) in known:
            continue
        pieces = path.stem.split("_")
        if len(pieces) < 2:
            continue
        root_id = "_".join(pieces[:2])
        tile = roots.get(root_id)
        if tile is None:
            continue
        tile = dict(tile)
        valid = True
        for suffix in pieces[2:]:
            if not suffix.startswith("s") or not suffix[1:].isdigit() or int(suffix[1:]) not in range(4):
                valid = False
                break
            tile = subdivide_tile(tile)[int(suffix[1:])]
        if not valid:
            continue
        payload = path.read_bytes()
        osm_base, element_count = _payload_metadata(payload)
        bbox = tuple(tile["bbox_south_west_north_east"])
        query = build_overpass_query(bbox)
        recovered.append({
            "tile_id": path.stem,
            "bbox_south_west_north_east": json.dumps(bbox, separators=(",", ":")),
            "query": query,
            "endpoint": endpoint,
            "requested_url": _overpass_url(endpoint, query),
            "retrieved_at_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            "retrieval_time_status": "filesystem_mtime_recovered",
            "status": "retained_superseded_raw",
            "http_status": 200,
            "saved_path": str(path),
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "osm_base_timestamp": osm_base,
            "element_count": element_count,
            "attempts": "unknown_recovered",
            "error": "",
        })
    return recovered


def acquire_tiles_with_subdivision(
    tiles: list[dict],
    raw_root: Path,
    *,
    fetcher=fetch_url,
    endpoint: str = DEFAULT_OVERPASS_ENDPOINT,
    retry_attempts: int = 2,
    sleep_seconds: float = 1.0,
    max_subdivide_depth: int = 2,
    request_timeout_seconds: int = 60,
    target_polygons=None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    def visit(tile: dict, depth: int, parent_tile_id: str) -> None:
        if target_polygons is not None:
            selected, skipped = partition_tiles_by_target_polygon([tile], target_polygons)
            if not selected:
                results.append({
                    **skipped[0],
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "saved_path": "",
                    "bytes": 0,
                    "sha256": "",
                    "element_count": 0,
                    "error": "",
                    "subdivision_depth": depth,
                    "parent_tile_id": parent_tile_id,
                })
                return
        row = acquire_tiles(
            [tile], raw_root, fetcher=fetcher, endpoint=endpoint,
            retry_attempts=retry_attempts, sleep_seconds=sleep_seconds,
            request_timeout_seconds=request_timeout_seconds,
        )[0]
        row["subdivision_depth"] = depth
        row["parent_tile_id"] = parent_tile_id
        if row["status"] in {"downloaded", "cached"} or depth >= max_subdivide_depth:
            results.append(row)
            return
        original_status = str(row["status"])
        row["status"] = f"subdivided_after_{original_status}"
        results.append(row)
        for child in subdivide_tile(tile):
            visit(child, depth + 1, str(tile["tile_id"]))

    for tile in tiles:
        visit(tile, 0, "")
    return results


def acquire_boundaries(destination: Path, fetcher=fetch_url) -> dict[str, object]:
    if destination.exists():
        payload = destination.read_bytes()
        status = "cached"
    else:
        http_status, payload, _ = fetcher(BOUNDARY_URL, 180)
        if http_status != 200:
            raise RuntimeError(f"boundary HTTP status {http_status}")
        decoded = json.loads(payload)
        load_target_polygons(decoded, TARGET_RELATION_IDS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".geojson.part")
        temporary.write_bytes(payload)
        temporary.replace(destination)
        status = "downloaded"
    decoded = json.loads(payload)
    load_target_polygons(decoded, TARGET_RELATION_IDS)
    return {
        "status": status,
        "url": BOUNDARY_URL,
        "saved_path": str(destination),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "relation_ids": sorted(TARGET_RELATION_IDS),
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        if not fields:
            return
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_optional_parquet(rows: list[dict], path: Path, writer="auto") -> str:
    if writer is None:
        return "unavailable_no_writer"
    try:
        if writer == "auto":
            import pandas as pd

            pd.DataFrame(rows).to_parquet(path, index=False)
        else:
            writer(rows, path)
        return "written"
    except (ImportError, ModuleNotFoundError) as exc:
        if path.exists():
            path.unlink()
        return f"unavailable_missing_engine:{type(exc).__name__}"


def _json_cell_row(row: dict) -> dict:
    converted = dict(row)
    for key in ("osm_way_ids", "highway_classes", "road_groups", "surface_values"):
        converted[key] = json.dumps(converted.get(key, []), ensure_ascii=False, separators=(",", ":"))
    return converted


def process_tiles(
    raw_root: Path,
    boundary_path: Path,
    processed_root: Path,
    evidence_root: Path,
    acquisition_rows: list[dict],
    *,
    target_relation_ids: set[int] = TARGET_RELATION_IDS,
    parquet_writer="auto",
    features_root: Path | None = None,
) -> dict[str, object]:
    processed_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)
    all_elements = []
    used_tiles = []
    for row in acquisition_rows:
        if row.get("status") not in {"downloaded", "cached"}:
            continue
        path = Path(str(row["saved_path"]))
        payload = json.loads(path.read_text(encoding="utf-8"))
        all_elements.extend(parse_overpass_elements(payload))
        used_tiles.append(str(row["tile_id"]))
    merged = deduplicate_elements(all_elements)
    nodes = {key[1]: element for key, element in merged.items() if key[0] == "node"}
    raw_ways = [element for key, element in merged.items() if key[0] == "way"]
    reconstructed = [reconstruct_way_parts(nodes, way) for way in raw_ways]
    boundary_geojson = json.loads(boundary_path.read_text(encoding="utf-8"))
    polygons = load_target_polygons(boundary_geojson, target_relation_ids)
    prepared_polygons = prepare_polygons(polygons)
    island_indexes = {
        relation_id: prepare_polygons(load_target_polygons(boundary_geojson, {relation_id}))
        for relation_id in sorted(target_relation_ids)
    }

    def island_for_point(longitude: float, latitude: float) -> tuple[int | str, str]:
        for relation_id, index in island_indexes.items():
            if point_in_multipolygon(longitude, latitude, index):
                return relation_id, TARGET_RELATION_NAMES.get(relation_id, f"OSM relation {relation_id}")
        return "", "unassigned"

    def island_for_parts(parts) -> tuple[int | str, str]:
        for part in parts:
            for longitude, latitude in part:
                relation_id, name = island_for_point(longitude, latitude)
                if relation_id != "":
                    return relation_id, name
            for first, second in zip(part, part[1:]):
                relation_id, name = island_for_point(
                    (first[0] + second[0]) / 2.0,
                    (first[1] + second[1]) / 2.0,
                )
                if relation_id != "":
                    return relation_id, name
        return "", "unassigned"

    inside = []
    incomplete = []
    for way in reconstructed:
        if way["missing_node_ids"]:
            incomplete.append(int(way["osm_way_id"]))
        clipped = clip_parts_to_target(way["parts"], prepared_polygons)
        if not clipped:
            continue
        island_id, island_name = island_for_parts(clipped)
        inside.append({
            **way, "parts": clipped,
            "island_osm_relation_id": island_id,
            "island_name": island_name,
        })

    centerline_path = processed_root / "osm_road_centerlines.geojsonl"
    with centerline_path.open("w", encoding="utf-8") as handle:
        for way in sorted(inside, key=lambda row: int(row["osm_way_id"])):
            classification = classify_vehicle_route(way["tags"])
            coordinates = way["parts"]
            geometry = {"type": "LineString", "coordinates": coordinates[0]}
            if len(coordinates) > 1:
                geometry = {"type": "MultiLineString", "coordinates": coordinates}
            feature = {
                "type": "Feature",
                "properties": {
                    "osm_way_id": int(way["osm_way_id"]),
                    "osm_version": int(way["version"]),
                    "island_osm_relation_id": way["island_osm_relation_id"],
                    "island_name": way["island_name"],
                    **way["tags"],
                    **classification,
                    "source": "OpenStreetMap auxiliary road data",
                    "attribution": ATTRIBUTION,
                },
                "geometry": geometry,
            }
            handle.write(json.dumps(feature, ensure_ascii=False, separators=(",", ":")) + "\n")

    cells = aggregate_road_cells(inside, prepared_polygons)
    cells_by_island: dict[str, int] = {}
    for cell in cells:
        island_name = str(cell["island_name"])
        cells_by_island[island_name] = cells_by_island.get(island_name, 0) + 1
    csv_rows = [_json_cell_row(row) for row in cells]
    cells_csv = processed_root / "osm_road_candidate_cells.csv"
    _write_csv(cells_csv, csv_rows)
    parquet_status = write_optional_parquet(csv_rows, processed_root / "osm_road_candidate_cells.parquet", parquet_writer)

    definitions = {
        "dataset": "osm_road_candidate_cells",
        "source_class": "auxiliary",
        "source": "OpenStreetMap",
        "attribution": ATTRIBUTION,
        "target_relation_ids": sorted(target_relation_ids),
        "grid": "UTM zone 52N, 100 m square cells",
        "normal_route_rule": "vehicle-capable highway class or explicit vehicle permission; explicit no/private excluded",
        "unknown_policy": "missing surface, width, lanes, access, or condition remains missing and is not inferred",
        "geometry_method": "OSM node geometry; segment lengths split exactly at 100 m grid boundaries; cell inclusion tested against target-island polygon",
    }
    if features_root is not None:
        features_root.mkdir(parents=True, exist_ok=True)
        (features_root / "osm_road_feature_definitions.json").write_text(
            json.dumps(definitions, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    classified_inside = [(way, classify_vehicle_route(way["tags"])) for way in inside]
    normal_inside = sum(bool(classification["normal_route"]) for _, classification in classified_inside)
    normal_by_highway = Counter(
        str(way["tags"].get("highway", "missing"))
        for way, classification in classified_inside if classification["normal_route"]
    )
    excluded_by_status = Counter(
        str(classification["vehicle_status"])
        for _, classification in classified_inside if not classification["normal_route"]
    )
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "OpenStreetMap auxiliary road data",
        "attribution": ATTRIBUTION,
        "target_relation_ids": sorted(target_relation_ids),
        "tiles_configured": len(acquisition_rows),
        "tiles_used": len(used_tiles),
        "tile_ids_used": used_tiles,
        "raw_elements": len(all_elements),
        "deduplicated_elements": len(merged),
        "deduplicated_nodes": len(nodes),
        "deduplicated_ways": len(raw_ways),
        "ways_inside_target": len(inside),
        "ways_outside_target": len(raw_ways) - len(inside),
        "normal_route_ways_inside_target": normal_inside,
        "normal_route_ways_by_highway": dict(sorted(normal_by_highway.items())),
        "restricted_or_nonvehicle_ways_inside_target": len(inside) - normal_inside,
        "restricted_or_nonvehicle_ways_by_status": dict(sorted(excluded_by_status.items())),
        "incomplete_way_count": len(incomplete),
        "incomplete_way_ids": incomplete,
        "candidate_cell_count": len(cells),
        "candidate_cells_by_island": dict(sorted(cells_by_island.items())),
        "candidate_road_length_m": round(sum(float(row["road_length_m"]) for row in cells), 3),
        "parquet_status": parquet_status,
        "official_status": "auxiliary_not_official",
    }
    audit_path = processed_root / "osm_processing_audit.json"
    audit_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    evidence_paths = [boundary_path, centerline_path, cells_csv, audit_path]
    acquisition_manifest_path = raw_root.parent / "osm_acquisition_manifest.csv"
    if acquisition_manifest_path.exists():
        evidence_paths.append(acquisition_manifest_path)
    if features_root is not None:
        evidence_paths.append(features_root / "osm_road_feature_definitions.json")
    parquet_path = processed_root / "osm_road_candidate_cells.parquet"
    if parquet_path.exists():
        evidence_paths.append(parquet_path)
    evidence_rows = []
    for path in sorted(evidence_paths):
        evidence_rows.append({
            "path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path),
            "source_class": "raw" if path in {boundary_path, acquisition_manifest_path} else "processed",
        })
    for path in sorted(raw_root.glob("*.json")):
        evidence_rows.append({
            "path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path),
            "source_class": "raw", "tile_id": path.stem,
        })
    _write_csv(evidence_root / "osm_road_evidence_manifest.csv", evidence_rows)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--columns", type=int, default=6)
    parser.add_argument("--rows", type=int, default=6)
    parser.add_argument("--endpoint", default=DEFAULT_OVERPASS_ENDPOINT)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--request-timeout-seconds", type=int, default=60)
    parser.add_argument("--max-subdivide-depth", type=int, default=2)
    args = parser.parse_args()

    raw_root = PROJECT_ROOT / "02_raw_road" / "osm_overpass_tiles"
    boundary_path = PROJECT_ROOT / "02_raw_road" / "osm_island_boundaries.geojson"
    processed_root = PROJECT_ROOT / "04_processed_road"
    evidence_root = PROJECT_ROOT / "12_evidence"
    features_root = PROJECT_ROOT / "07_features"
    tiles = build_bbox_tiles(AMAMI_MAIN_ISLAND_BBOX, columns=args.columns, rows=args.rows)
    boundary_row = acquire_boundaries(boundary_path)
    boundary_geojson = json.loads(boundary_path.read_text(encoding="utf-8"))
    polygons = load_target_polygons(boundary_geojson, TARGET_RELATION_IDS)
    selected_tiles, skipped_tiles = partition_tiles_by_target_polygon(tiles, polygons)
    rows = acquire_tiles_with_subdivision(
        selected_tiles, raw_root, endpoint=args.endpoint,
        retry_attempts=args.retries, sleep_seconds=args.sleep_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
        max_subdivide_depth=args.max_subdivide_depth,
        target_polygons=polygons,
    )
    rows.extend({
        **tile,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "saved_path": "",
        "bytes": 0,
        "sha256": "",
        "element_count": 0,
        "error": "",
    } for tile in skipped_tiles)
    rows.sort(key=lambda row: str(row["tile_id"]))
    recovered_rows = recover_unreferenced_raw_rows(raw_root, rows, tiles, args.endpoint)
    manifest_rows = [{"record_type": "island_boundary", **boundary_row}] + [
        {"record_type": "road_tile", **row} for row in rows
    ] + [
        {"record_type": "road_tile_retained_not_used", **row} for row in recovered_rows
    ]
    manifest_path = PROJECT_ROOT / "02_raw_road" / "osm_acquisition_manifest.csv"
    _write_csv(manifest_path, manifest_rows)
    summary = process_tiles(
        raw_root, boundary_path, processed_root, evidence_root, rows,
        features_root=features_root,
    )
    summary["acquisition_manifest"] = str(manifest_path)
    summary["failed_tiles"] = [
        row["tile_id"] for row in rows
        if row["status"] not in {"downloaded", "cached"}
        and row["status"] not in {"outside_target_polygon"}
        and not str(row["status"]).startswith("subdivided_after_")
    ]
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
