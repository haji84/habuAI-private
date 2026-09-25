from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Iterable

from src.gpx_audit import utm52n
from src.terrain_road_features import inverse_utm52n


BASE_VEHICLE_HIGHWAYS = {
    "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
    "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified",
    "residential", "living_street", "service", "track", "road",
}
EXPLICIT_ALLOW = {"yes", "designated", "permissive", "destination"}
EXPLICIT_DENY = {"no", "private"}


def build_bbox_tiles(
    bbox_west_south_east_north: tuple[float, float, float, float],
    columns: int = 6,
    rows: int = 6,
) -> list[dict[str, object]]:
    if columns < 1 or rows < 1:
        raise ValueError("columns and rows must be positive")
    west, south, east, north = bbox_west_south_east_north
    if not west < east or not south < north:
        raise ValueError("invalid bbox")
    dx = (east - west) / columns
    dy = (north - south) / rows
    result = []
    for row in range(rows):
        tile_south = south + row * dy
        tile_north = north if row == rows - 1 else south + (row + 1) * dy
        for column in range(columns):
            tile_west = west + column * dx
            tile_east = east if column == columns - 1 else west + (column + 1) * dx
            result.append(
                {
                    "tile_id": f"r{row:02d}_c{column:02d}",
                    "bbox_south_west_north_east": (
                        round(tile_south, 12), round(tile_west, 12),
                        round(tile_north, 12), round(tile_east, 12),
                    ),
                }
            )
    return result


def parse_overpass_elements(payload: dict) -> list[dict]:
    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise ValueError("Overpass response has no elements list")
    parsed = []
    for element in elements:
        if not isinstance(element, dict) or element.get("type") not in {"node", "way", "relation"}:
            continue
        if not isinstance(element.get("id"), int):
            raise ValueError("OSM element has no integer id")
        parsed.append(element)
    return parsed


def _canonical_element(element: dict) -> str:
    return json.dumps(element, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deduplicate_elements(elements: Iterable[dict]) -> dict[tuple[str, int], dict]:
    merged: dict[tuple[str, int], dict] = {}
    for element in elements:
        key = (str(element["type"]), int(element["id"]))
        current = merged.get(key)
        if current is None:
            merged[key] = element
            continue
        old_version = int(current.get("version", 0) or 0)
        new_version = int(element.get("version", 0) or 0)
        if new_version > old_version:
            merged[key] = element
        elif new_version == old_version and _canonical_element(element) != _canonical_element(current):
            raise ValueError(f"contradictory equal-version OSM element: {key}")
    return merged


def classify_vehicle_route(tags: dict | None) -> dict[str, object]:
    original = dict(tags or {})
    normalized = {str(key): str(value).strip().lower() for key, value in original.items()}
    highway = normalized.get("highway", "")
    access_values = [normalized.get(key, "") for key in ("motor_vehicle", "vehicle", "access")]
    denied = next((value for value in access_values if value in EXPLICIT_DENY), "")
    if denied:
        status = "restricted" if denied == "private" else "prohibited"
        return {
            "normal_route": False,
            "vehicle_status": status,
            "road_group": _road_group(highway),
            "classification_reason": f"explicit_access_{denied}",
        }
    explicitly_allowed = any(value in EXPLICIT_ALLOW for value in access_values)
    if highway in BASE_VEHICLE_HIGHWAYS:
        return {
            "normal_route": True,
            "vehicle_status": _road_group(highway),
            "road_group": _road_group(highway),
            "classification_reason": "vehicle_highway_class",
        }
    if explicitly_allowed:
        return {
            "normal_route": True,
            "vehicle_status": "explicit_vehicle",
            "road_group": "explicit_vehicle",
            "classification_reason": "explicit_vehicle_access",
        }
    return {
        "normal_route": False,
        "vehicle_status": "non_vehicle",
        "road_group": "non_vehicle",
        "classification_reason": "no_vehicle_evidence",
    }


def _road_group(highway: str) -> str:
    base = highway.removesuffix("_link")
    if base in {"motorway", "trunk", "primary", "secondary"}:
        return "arterial"
    if base in {"tertiary", "unclassified"}:
        return "regional"
    if base in {"residential", "living_street"}:
        return "local"
    if base in {"service", "track", "road"}:
        return base
    return "other"


def reconstruct_way_parts(nodes: dict[int, dict], way: dict) -> dict[str, object]:
    parts: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    missing: list[int] = []
    for raw_node_id in way.get("nodes", []):
        node_id = int(raw_node_id)
        node = nodes.get(node_id)
        if node is None or "lat" not in node or "lon" not in node:
            missing.append(node_id)
            if len(current) >= 2:
                parts.append(current)
            current = []
            continue
        current.append((float(node["lon"]), float(node["lat"])))
    if len(current) >= 2:
        parts.append(current)
    return {
        "osm_way_id": int(way["id"]),
        "version": int(way.get("version", 0) or 0),
        "tags": dict(way.get("tags", {})),
        "parts": parts,
        "missing_node_ids": missing,
    }


def load_target_polygons(geojson: dict, relation_ids: set[int]) -> list[list[list[tuple[float, float]]]]:
    polygons: list[list[list[tuple[float, float]]]] = []
    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})
        osm_id = properties.get("osm_id")
        if osm_id is None or int(osm_id) not in relation_ids:
            continue
        geometry = feature.get("geometry") or {}
        kind = geometry.get("type")
        coordinates = geometry.get("coordinates") or []
        raw_polygons = [coordinates] if kind == "Polygon" else coordinates if kind == "MultiPolygon" else []
        for raw_polygon in raw_polygons:
            rings = []
            for ring in raw_polygon:
                rings.append([(float(point[0]), float(point[1])) for point in ring])
            if rings:
                polygons.append(rings)
    if not polygons:
        raise ValueError("target island polygons not found")
    return polygons


def partition_tiles_by_target_bbox(
    tiles: list[dict],
    polygons: list[list[list[tuple[float, float]]]],
) -> tuple[list[dict], list[dict]]:
    polygon_bounds = []
    for polygon in polygons:
        outer = polygon[0]
        longitudes = [point[0] for point in outer]
        latitudes = [point[1] for point in outer]
        polygon_bounds.append((min(longitudes), min(latitudes), max(longitudes), max(latitudes)))
    selected = []
    skipped = []
    for tile in tiles:
        south, west, north, east = tuple(tile["bbox_south_west_north_east"])
        overlaps = any(
            west <= polygon_east and east >= polygon_west
            and south <= polygon_north and north >= polygon_south
            for polygon_west, polygon_south, polygon_east, polygon_north in polygon_bounds
        )
        if overlaps:
            selected.append(tile)
        else:
            skipped.append({**tile, "status": "outside_target_polygon_bbox"})
    return selected, skipped


def _orientation(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def _segments_intersect(a, b, c, d) -> bool:
    if _point_on_segment(c[0], c[1], a[0], a[1], b[0], b[1]):
        return True
    if _point_on_segment(d[0], d[1], a[0], a[1], b[0], b[1]):
        return True
    if _point_on_segment(a[0], a[1], c[0], c[1], d[0], d[1]):
        return True
    if _point_on_segment(b[0], b[1], c[0], c[1], d[0], d[1]):
        return True
    first = _orientation(*a, *b, *c)
    second = _orientation(*a, *b, *d)
    third = _orientation(*c, *d, *a)
    fourth = _orientation(*c, *d, *b)
    return (first > 0) != (second > 0) and (third > 0) != (fourth > 0)


def _tile_intersects_target_polygon(
    tile: dict,
    polygons: list[list[list[tuple[float, float]]]],
) -> bool:
    south, west, north, east = tuple(tile["bbox_south_west_north_east"])
    corners = [(west, south), (east, south), (east, north), (west, north)]
    if any(point_in_multipolygon(lon, lat, polygons) for lon, lat in corners):
        return True
    rectangle_edges = list(zip(corners, corners[1:] + corners[:1]))
    for polygon in polygons:
        outer = polygon[0]
        if any(west <= lon <= east and south <= lat <= north for lon, lat in outer):
            return True
        for first, second in zip(outer, outer[1:]):
            if any(_segments_intersect(first, second, edge_start, edge_end) for edge_start, edge_end in rectangle_edges):
                return True
    return False


def partition_tiles_by_target_polygon(
    tiles: list[dict],
    polygons: list[list[list[tuple[float, float]]]],
) -> tuple[list[dict], list[dict]]:
    selected = []
    skipped = []
    for tile in tiles:
        if _tile_intersects_target_polygon(tile, polygons):
            selected.append(tile)
        else:
            skipped.append({**tile, "status": "outside_target_polygon"})
    return selected, skipped


def _point_on_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> bool:
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    tolerance = 1e-10 * max(1.0, abs(bx - ax) + abs(by - ay))
    if abs(cross) > tolerance:
        return False
    return min(ax, bx) - tolerance <= px <= max(ax, bx) + tolerance and min(ay, by) - tolerance <= py <= max(ay, by) + tolerance


def _point_in_ring(px: float, py: float, ring: list[tuple[float, float]]) -> tuple[bool, bool]:
    inside = False
    for index in range(len(ring)):
        ax, ay = ring[index - 1]
        bx, by = ring[index]
        if _point_on_segment(px, py, ax, ay, bx, by):
            return True, True
        if (ay > py) != (by > py):
            crossing_x = (bx - ax) * (py - ay) / (by - ay) + ax
            if px < crossing_x:
                inside = not inside
    return inside, False


def prepare_polygons(
    polygons: list[list[list[tuple[float, float]]]],
    bin_size_degrees: float = 0.01,
) -> dict[str, object]:
    if bin_size_degrees <= 0:
        raise ValueError("bin_size_degrees must be positive")
    prepared_polygons = []
    for polygon in polygons:
        prepared_rings = []
        for ring in polygon:
            longitudes = [point[0] for point in ring]
            latitudes = [point[1] for point in ring]
            bins: dict[int, list[tuple[tuple[float, float], tuple[float, float]]]] = defaultdict(list)
            for first, second in zip(ring, ring[1:]):
                start_bin = math.floor(min(first[1], second[1]) / bin_size_degrees)
                end_bin = math.floor(max(first[1], second[1]) / bin_size_degrees)
                for bin_index in range(start_bin, end_bin + 1):
                    bins[bin_index].append((first, second))
            prepared_rings.append({
                "bounds": (min(longitudes), min(latitudes), max(longitudes), max(latitudes)),
                "bins": dict(bins),
            })
        prepared_polygons.append(prepared_rings)
    return {
        "_prepared_polygon_index": True,
        "bin_size_degrees": bin_size_degrees,
        "polygons": prepared_polygons,
    }


def _point_in_prepared_ring(px: float, py: float, prepared_ring: dict, bin_size: float) -> tuple[bool, bool]:
    west, south, east, north = prepared_ring["bounds"]
    if px < west or px > east or py < south or py > north:
        return False, False
    inside = False
    edges = prepared_ring["bins"].get(math.floor(py / bin_size), [])
    for (ax, ay), (bx, by) in edges:
        if _point_on_segment(px, py, ax, ay, bx, by):
            return True, True
        if (ay > py) != (by > py):
            crossing_x = (bx - ax) * (py - ay) / (by - ay) + ax
            if px < crossing_x:
                inside = not inside
    return inside, False


def point_in_multipolygon(
    longitude: float,
    latitude: float,
    polygons,
) -> bool:
    if isinstance(polygons, dict) and polygons.get("_prepared_polygon_index"):
        bin_size = float(polygons["bin_size_degrees"])
        for polygon in polygons["polygons"]:
            outer_inside, outer_boundary = _point_in_prepared_ring(longitude, latitude, polygon[0], bin_size)
            if not outer_inside:
                continue
            if outer_boundary:
                return True
            in_hole = False
            for hole in polygon[1:]:
                hole_inside, hole_boundary = _point_in_prepared_ring(longitude, latitude, hole, bin_size)
                if hole_boundary:
                    return True
                if hole_inside:
                    in_hole = True
                    break
            if not in_hole:
                return True
        return False
    for polygon in polygons:
        outer_inside, outer_boundary = _point_in_ring(longitude, latitude, polygon[0])
        if not outer_inside:
            continue
        if outer_boundary:
            return True
        in_hole = False
        for hole in polygon[1:]:
            hole_inside, hole_boundary = _point_in_ring(longitude, latitude, hole)
            if hole_boundary:
                return True
            if hole_inside:
                in_hole = True
                break
        if not in_hole:
            return True
    return False


def segment_grid_contributions_xy(x1: float, y1: float, x2: float, y2: float) -> list[dict[str, float | int]]:
    dx, dy = x2 - x1, y2 - y1
    total_length = math.hypot(dx, dy)
    if total_length == 0:
        return []
    breakpoints = {0.0, 1.0}
    if dx:
        first = math.floor(min(x1, x2) / 100.0) + 1
        last = math.floor(max(x1, x2) / 100.0)
        for boundary_index in range(first, last + 1):
            t = (boundary_index * 100.0 - x1) / dx
            if 0.0 < t < 1.0:
                breakpoints.add(t)
    if dy:
        first = math.floor(min(y1, y2) / 100.0) + 1
        last = math.floor(max(y1, y2) / 100.0)
        for boundary_index in range(first, last + 1):
            t = (boundary_index * 100.0 - y1) / dy
            if 0.0 < t < 1.0:
                breakpoints.add(t)
    ordered = sorted(breakpoints)
    rows = []
    for start, end in zip(ordered, ordered[1:]):
        midpoint = (start + end) / 2.0
        mid_x = x1 + dx * midpoint
        mid_y = y1 + dy * midpoint
        rows.append(
            {
                "cell_x_index": math.floor(mid_x / 100.0),
                "cell_y_index": math.floor(mid_y / 100.0),
                "length_m": total_length * (end - start),
                "midpoint_x": mid_x,
                "midpoint_y": mid_y,
                "bearing_deg": (math.degrees(math.atan2(dx, dy)) + 360.0) % 180.0,
            }
        )
    return rows


def clip_parts_to_target(
    parts: list[list[tuple[float, float]]],
    polygons: list[list[list[tuple[float, float]]]],
) -> list[list[tuple[float, float]]]:
    kept = []
    for part in parts:
        if any(point_in_multipolygon(lon, lat, polygons) for lon, lat in part):
            kept.append(part)
            continue
        for first, second in zip(part, part[1:]):
            lon = (first[0] + second[0]) / 2.0
            lat = (first[1] + second[1]) / 2.0
            if point_in_multipolygon(lon, lat, polygons):
                kept.append(part)
                break
    return kept


def road_cells_100m(
    way: dict,
    polygons: list[list[list[tuple[float, float]]]],
) -> list[dict[str, object]]:
    classification = classify_vehicle_route(way.get("tags", {}))
    if not classification["normal_route"]:
        return []
    rows = []
    for part in way.get("parts", []):
        for first, second in zip(part, part[1:]):
            x1, y1 = utm52n(first[1], first[0])
            x2, y2 = utm52n(second[1], second[0])
            for contribution in segment_grid_contributions_xy(x1, y1, x2, y2):
                lat, lon = inverse_utm52n(float(contribution["midpoint_x"]), float(contribution["midpoint_y"]))
                if not point_in_multipolygon(lon, lat, polygons):
                    continue
                rows.append(
                    {
                        **contribution,
                        "osm_way_id": int(way["osm_way_id"]),
                        "island_osm_relation_id": way.get("island_osm_relation_id", ""),
                        "island_name": way.get("island_name", ""),
                        "tags": dict(way.get("tags", {})),
                        **classification,
                    }
                )
    return rows


def aggregate_road_cells(
    ways: Iterable[dict],
    polygons,
) -> list[dict[str, object]]:
    if not (isinstance(polygons, dict) and polygons.get("_prepared_polygon_index")):
        polygons = prepare_polygons(polygons)
    grouped: dict[tuple[int, int], list[dict[str, object]]] = defaultdict(list)
    for way in ways:
        for row in road_cells_100m(way, polygons):
            grouped[(int(row["cell_x_index"]), int(row["cell_y_index"]))].append(row)
    output = []
    for (cell_x, cell_y), rows in sorted(grouped.items()):
        length = sum(float(row["length_m"]) for row in rows)
        sin_sum = sum(float(row["length_m"]) * math.sin(math.radians(2 * float(row["bearing_deg"]))) for row in rows)
        cos_sum = sum(float(row["length_m"]) * math.cos(math.radians(2 * float(row["bearing_deg"]))) for row in rows)
        direction = (math.degrees(math.atan2(sin_sum, cos_sum)) / 2.0 + 180.0) % 180.0
        center_x, center_y = cell_x * 100.0 + 50.0, cell_y * 100.0 + 50.0
        center_lat, center_lon = inverse_utm52n(center_x, center_y)
        tags = [row["tags"] for row in rows]
        way_ids = sorted({int(row["osm_way_id"]) for row in rows})
        island_ids = {row.get("island_osm_relation_id", "") for row in rows if row.get("island_osm_relation_id", "") != ""}
        island_names = {str(row.get("island_name", "")) for row in rows if row.get("island_name", "")}
        if len(island_ids) > 1 or len(island_names) > 1:
            raise ValueError(f"100m cell spans multiple target islands: {(cell_x, cell_y)}")
        classes = sorted({str(tag.get("highway", "")) for tag in tags if tag.get("highway")})
        groups = sorted({str(row["road_group"]) for row in rows})
        surfaces = sorted({str(tag.get("surface", "")) for tag in tags if tag.get("surface")})
        output.append(
            {
                "cell_id": f"utm52n_100m_{cell_x}_{cell_y}",
                "cell_x_index": cell_x,
                "cell_y_index": cell_y,
                "cell_center_x": round(center_x, 3),
                "cell_center_y": round(center_y, 3),
                "cell_center_latitude": round(center_lat, 8),
                "cell_center_longitude": round(center_lon, 8),
                "normal_route": True,
                "road_length_m": round(length, 3),
                "road_density_m_per_ha": round(length, 3),
                "segment_count": len(rows),
                "osm_way_ids": way_ids,
                "island_osm_relation_id": next(iter(island_ids), ""),
                "island_name": next(iter(island_names), ""),
                "highway_classes": classes,
                "road_groups": groups,
                "surface_values": surfaces,
                "surface_missing": any(not tag.get("surface") for tag in tags),
                "bridge_present": any(str(tag.get("bridge", "")).lower() not in {"", "no"} for tag in tags),
                "tunnel_present": any(str(tag.get("tunnel", "")).lower() not in {"", "no"} for tag in tags),
                "road_direction_deg": round(direction, 6),
                "source": "OpenStreetMap auxiliary road data",
                "candidate_source": "osm_auxiliary",
            }
        )
    return output
