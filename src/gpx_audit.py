from __future__ import annotations

import math
import csv
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def utm52n(latitude: float, longitude: float) -> tuple[float, float]:
    """Convert WGS84 latitude/longitude to UTM zone 52N metres."""
    a = 6378137.0
    ecc_sq = 0.00669437999014
    k0 = 0.9996
    lat = math.radians(latitude)
    lon = math.radians(longitude)
    lon0 = math.radians(129.0)
    ecc_prime_sq = ecc_sq / (1.0 - ecc_sq)
    n = a / math.sqrt(1.0 - ecc_sq * math.sin(lat) ** 2)
    t = math.tan(lat) ** 2
    c = ecc_prime_sq * math.cos(lat) ** 2
    aa = math.cos(lat) * (lon - lon0)
    m = a * (
        (1 - ecc_sq / 4 - 3 * ecc_sq**2 / 64 - 5 * ecc_sq**3 / 256) * lat
        - (3 * ecc_sq / 8 + 3 * ecc_sq**2 / 32 + 45 * ecc_sq**3 / 1024) * math.sin(2 * lat)
        + (15 * ecc_sq**2 / 256 + 45 * ecc_sq**3 / 1024) * math.sin(4 * lat)
        - (35 * ecc_sq**3 / 3072) * math.sin(6 * lat)
    )
    easting = k0 * n * (
        aa
        + (1 - t + c) * aa**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * ecc_prime_sq) * aa**5 / 120
    ) + 500000.0
    northing = k0 * (
        m
        + n * math.tan(lat) * (
            aa**2 / 2
            + (5 - t + 9 * c + 4 * c**2) * aa**4 / 24
            + (61 - 58 * t + t**2 + 600 * c - 330 * ecc_prime_sq) * aa**6 / 720
        )
    )
    return easting, northing


def distance_m(a: dict, b: dict) -> float:
    x1, y1 = utm52n(float(a["latitude"]), float(a["longitude"]))
    x2, y2 = utm52n(float(b["latitude"]), float(b["longitude"]))
    return math.hypot(x2 - x1, y2 - y1)


def mark_point_anomalies(points: list[dict]) -> list[dict]:
    marked = [dict(point, exclude_point=False, anomaly_reason="", segment_break_before=False) for point in points]
    # A GPS spike can persist for a few samples.  If a >500 m excursion returns
    # within 30 seconds to within 100 m of its origin, exclude only that bounded
    # excursion.  This does not bridge or invent any travelled path.
    for start in range(len(marked) - 2):
        if marked[start]["exclude_point"]:
            continue
        first = start + 1
        if distance_m(marked[start], marked[first]) <= 500:
            continue
        for end in range(first + 1, min(len(marked), first + 31)):
            elapsed = (marked[end]["time_utc"] - marked[start]["time_utc"]).total_seconds()
            if elapsed > 30:
                break
            if distance_m(marked[start], marked[end]) < 100:
                for index in range(first, end):
                    marked[index]["exclude_point"] = True
                    marked[index]["anomaly_reason"] = "bounded_gps_excursion"
                break
    for i in range(1, len(marked) - 1):
        previous, current, following = marked[i - 1], marked[i], marked[i + 1]
        dt1 = (current["time_utc"] - previous["time_utc"]).total_seconds()
        dt2 = (following["time_utc"] - current["time_utc"]).total_seconds()
        if 0 < dt1 <= 30 and 0 < dt2 <= 30:
            if distance_m(previous, current) > 500 and distance_m(current, following) > 500 and distance_m(previous, following) < 100:
                current["exclude_point"] = True
                current["anomaly_reason"] = "isolated_gps_spike"

    last_valid_index: int | None = None
    for i, current in enumerate(marked):
        if current["exclude_point"]:
            continue
        if last_valid_index is not None:
            previous = marked[last_valid_index]
            dt = (current["time_utc"] - previous["time_utc"]).total_seconds()
            dist = distance_m(previous, current)
            if dt <= 0 or dt > 30 or (dist > 500 and dt <= 30):
                current["segment_break_before"] = True
                if not current["anomaly_reason"]:
                    current["anomaly_reason"] = "time_gap" if dt > 30 else "rapid_jump"
        last_valid_index = i
    return marked


def match_capture_to_points(capture: dict, points: list[dict]) -> dict:
    capture_time = datetime.fromisoformat(str(capture["datetime_jst"])).astimezone(timezone.utc)
    candidate = None
    for point in points:
        if point.get("exclude_point"):
            continue
        delta = abs((point["time_utc"] - capture_time).total_seconds())
        dist = distance_m(capture, point)
        key = (delta > 600, dist, delta)
        if candidate is None or key < candidate[0]:
            candidate = (key, point, dist, delta)
    base = {"event_id": capture.get("event_id", "")}
    if candidate is None:
        return {**base, "match_status": "unmatched_no_gpx_points", "distance_m": "", "time_delta_s": ""}
    _, point, dist, delta = candidate
    status = "matched_100m_10min" if dist <= 100 and delta <= 600 else "unmatched_threshold"
    return {
        **base,
        "match_status": status,
        "distance_m": dist,
        "time_delta_s": delta,
        "matched_time_utc": point["time_utc"].isoformat(),
        "matched_latitude": point["latitude"],
        "matched_longitude": point["longitude"],
        "matched_sequence": point.get("sequence", ""),
        "matched_source_gpx": point.get("source_gpx", ""),
    }


def parse_gpx(path: Path) -> list[dict]:
    points: list[dict] = []
    root = ET.parse(path).getroot()
    for sequence, element in enumerate(root.iter()):
        if not element.tag.endswith("trkpt"):
            continue
        values: dict[str, str] = {}
        for child in element.iter():
            tag = child.tag.rsplit("}", 1)[-1]
            if child.text and tag != "trkpt":
                values.setdefault(tag, child.text.strip())
        raw_time = values.get("time")
        if not raw_time:
            continue
        time_utc = datetime.fromisoformat(raw_time.replace("Z", "+00:00")).astimezone(timezone.utc)
        points.append(
            {
                "sequence": sequence,
                "time_utc": time_utc,
                "latitude": float(element.attrib["lat"]),
                "longitude": float(element.attrib["lon"]),
                "elevation_m": float(values["ele"]) if values.get("ele") else None,
                "speed_mps": float(values["speed"]) if values.get("speed") else None,
                "course_deg": float(values["course"]) if values.get("course") else None,
                "hdop": float(values["hdop"]) if values.get("hdop") else None,
                "source_gpx": path.name,
            }
        )
    return mark_point_anomalies(points)


JST = timezone(timedelta(hours=9))


def night_date_for_time(value: datetime) -> str:
    return (value.astimezone(JST) - timedelta(hours=7)).date().isoformat()


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def build_gpx_audit(gpx_dir: Path, events_csv: Path, captures_csv: Path, output_dir: Path) -> dict:
    all_points: list[dict] = []
    file_audit: list[dict] = []
    points_by_night: dict[str, list[dict]] = defaultdict(list)
    gpx_by_night: dict[str, list[str]] = defaultdict(list)
    for path in sorted(gpx_dir.glob("*.gpx")):
        points = parse_gpx(path)
        if not points:
            file_audit.append({"source_gpx": path.name, "point_count": 0, "audit_status": "invalid_no_points"})
            continue
        night = night_date_for_time(points[0]["time_utc"])
        role = "nonsearch_context" if path.name.startswith("2026-08-30-") else "complete_real_gpx"
        for point in points:
            point["night_date"] = night
            point["gpx_role"] = role
            x, y = utm52n(point["latitude"], point["longitude"])
            point["utm_x"] = round(x, 3)
            point["utm_y"] = round(y, 3)
            row = dict(point)
            row["time_utc"] = point["time_utc"].isoformat()
            all_points.append(row)
            if role == "complete_real_gpx":
                points_by_night[night].append(point)
        gpx_by_night[night].append(path.name)
        file_audit.append(
            {
                "source_gpx": path.name,
                "night_date": night,
                "gpx_role": role,
                "point_count": len(points),
                "valid_point_count": sum(not p["exclude_point"] for p in points),
                "excluded_point_count": sum(p["exclude_point"] for p in points),
                "segment_break_count": sum(p["segment_break_before"] for p in points),
                "start_utc": points[0]["time_utc"].isoformat(),
                "end_utc": points[-1]["time_utc"].isoformat(),
                "audit_status": "audited",
            }
        )

    events = _read_csv(events_csv)
    registry: dict[str, dict] = {}
    for event in events:
        night = event["night_date"]
        row = registry.setdefault(
            night,
            {
                "night_date": night,
                "log_event_count": 0,
                "capture_count": 0,
                "search_start_jst": "",
                "search_end_jst": "",
            },
        )
        row["log_event_count"] += 1
        row["capture_count"] += event["event_normalized"] == "capture"
        if event["event_normalized"] == "search_start":
            row["search_start_jst"] = min(filter(None, [row["search_start_jst"], event["datetime_jst"]]), default="")
        if event["event_normalized"] == "search_end":
            row["search_end_jst"] = max(filter(None, [row["search_end_jst"], event["datetime_jst"]]), default="")
    for night in set(registry) | set(gpx_by_night):
        row = registry.setdefault(night, {"night_date": night, "log_event_count": 0, "capture_count": 0, "search_start_jst": "", "search_end_jst": ""})
        names = gpx_by_night.get(night, [])
        row["gpx_files"] = "|".join(names)
        if any(not name.startswith("2026-08-30-") for name in names):
            row["gpx_status"] = "complete_real_gpx"
        elif names:
            row["gpx_status"] = "nonsearch_context_only"
        else:
            row["gpx_status"] = "not_acquired"
        row["eligible_for_exposure"] = row["gpx_status"] == "complete_real_gpx"

    capture_matches: list[dict] = []
    for capture in _read_csv(captures_csv):
        if capture.get("source_status") != "log_confirmed":
            continue
        base = {
            "event_id": capture.get("event_id", ""),
            "night_date": capture.get("night_date", ""),
            "datetime_jst": capture.get("datetime_jst", ""),
            "latitude": capture.get("latitude", ""),
            "longitude": capture.get("longitude", ""),
            "coordinate_quality": capture.get("coordinate_quality", ""),
        }
        if not capture.get("latitude") or not capture.get("longitude"):
            capture_matches.append({**base, "match_status": "unmatched_missing_capture_coordinate", "distance_m": "", "time_delta_s": ""})
            continue
        points = points_by_night.get(capture["night_date"], [])
        result = match_capture_to_points(capture, points)
        capture_matches.append({**base, **result})

    registry_rows = sorted(registry.values(), key=lambda r: r["night_date"])
    _write_csv(output_dir / "gpx_points_audited.csv", all_points)
    _write_csv(output_dir / "gpx_file_audit.csv", file_audit)
    _write_csv(output_dir / "night_registry_final.csv", registry_rows)
    _write_csv(output_dir / "capture_match_final.csv", capture_matches)
    summary = {
        "gpx_files_total": len(file_audit),
        "eligible_search_gpx_files": sum(r.get("gpx_role") == "complete_real_gpx" for r in file_audit),
        "nonsearch_context_gpx_files": sum(r.get("gpx_role") == "nonsearch_context" for r in file_audit),
        "gpx_points_total": len(all_points),
        "excluded_gps_anomaly_points": sum(bool(r["exclude_point"]) for r in all_points),
        "segment_breaks": sum(bool(r["segment_break_before"]) for r in all_points),
        "night_registry_rows": len(registry_rows),
        "log_confirmed_captures": len(capture_matches),
        "captures_matched_100m_10min": sum(r["match_status"] == "matched_100m_10min" for r in capture_matches),
    }
    (output_dir / "gpx_audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
