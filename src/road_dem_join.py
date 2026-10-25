"""Join verified EPSG:32652 DEM elevations to archived 100m road cells.

No terrain values are invented for cells outside raster support. A synthetic DEM
can be used in unit tests, never as actual Amami training evidence.
"""
from __future__ import annotations

import csv
import hashlib
import math
from datetime import datetime
from pathlib import Path


class TerrainSourceError(ValueError):
    pass


def digest_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _number(value: str) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise TerrainSourceError("Invalid numeric raster or road value") from exc
    if not math.isfinite(n):
        raise TerrainSourceError("Non-finite elevation/geometry")
    return n


def _aware(value: str) -> datetime:
    time = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if time.tzinfo is None or time.utcoffset() is None:
        raise TerrainSourceError("Source availability and cutoff need timezones")
    return time


def read_esri_ascii(path: Path) -> dict:
    """Accept only projected metre-based ESRI ASCII grids with corner origin."""
    text = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if len(text) < 9:
        raise TerrainSourceError("Incomplete DEM raster")
    info = {}
    for line in text[:6]:
        parts = line.split()
        if len(parts) != 2:
            raise TerrainSourceError("Invalid DEM header")
        key = parts[0].lower()
        if key in info:
            raise TerrainSourceError("Duplicate DEM header key")
        info[key] = parts[1]
    required = {"ncols", "nrows", "xllcorner", "yllcorner", "cellsize", "nodata_value"}
    if set(info) != required:
        raise TerrainSourceError("Expected EPSG:32652 corner-origin ASCII grid metadata")
    nc, nr = int(info["ncols"]), int(info["nrows"])
    step = _number(info["cellsize"])
    if not (3 <= nc <= 20000 and 3 <= nr <= 20000 and 0 < step <= 100):
        raise TerrainSourceError("DEM dimensions or resolution invalid")
    if len(text) != 6 + nr:
        raise TerrainSourceError("DEM row count mismatch")
    x0, y0 = _number(info["xllcorner"]), _number(info["yllcorner"])
    nodata = _number(info["nodata_value"])
    data = []
    for line in text[6:]:
        values = [_number(value) for value in line.split()]
        if len(values) != nc:
            raise TerrainSourceError("DEM column count mismatch")
        data.append(values)
    return {"ncols": nc, "nrows": nr, "x0": x0, "y0": y0,
            "cellsize": step, "nodata": nodata, "data": data}


def sample_gradient(grid: dict, x: float, y: float) -> dict | None:
    """Sample a 3x3 neighbourhood around the cell-centre in UTM metres."""
    col = math.floor((x - grid["x0"]) / grid["cellsize"])
    row_from_bottom = math.floor((y - grid["y0"]) / grid["cellsize"])
    row = grid["nrows"] - 1 - row_from_bottom
    if row <= 0 or col <= 0 or row >= grid["nrows"] - 1 or col >= grid["ncols"] - 1:
        return None
    window = [grid["data"][j][col-1:col+2] for j in range(row-1, row+2)]
    values = [v for line in window for v in line]
    if any(v == grid["nodata"] for v in values):
        return None
    step = grid["cellsize"]
    # Column increases east; row increases south. dy increases north.
    dz_dx = (window[1][2] - window[1][0]) / (2 * step)
    dz_dy = (window[0][1] - window[2][1]) / (2 * step)
    slope = math.degrees(math.atan(math.hypot(dz_dx, dz_dy)))
    downhill_east, downhill_north = -dz_dx, -dz_dy
    aspect = None if slope < 1e-9 else (math.degrees(math.atan2(
        downhill_east, downhill_north)) + 360.0) % 360.0
    center = window[1][1]
    neighbors = (sum(values) - center) / 8
    return {"elevation_m": center, "slope_deg": slope,
            "aspect_downslope_deg": aspect, "tpi_3x3_m": center-neighbors}


def join_road_dem(road_csv: Path, dem_ascii: Path, *,
                  road_sha256: str, dem_sha256: str, dem_epsg: int,
                  road_available_at: str, dem_available_at: str,
                  cutoff_time: str, wind_from_deg: float | None = None) -> dict:
    if dem_epsg != 32652:
        raise TerrainSourceError("Raster CRS must be explicitly EPSG:32652")
    cutoff = _aware(cutoff_time)
    if any(_aware(s) >= cutoff for s in (road_available_at, dem_available_at)):
        raise TerrainSourceError("Source only available at or after prospective cutoff")
    if digest_file(road_csv) != road_sha256 or digest_file(dem_ascii) != dem_sha256:
        raise TerrainSourceError("Road or DEM bytes failed declared SHA256")
    if wind_from_deg is not None and (type(wind_from_deg) not in (int, float)
                                      or not math.isfinite(wind_from_deg)
                                      or not 0 <= wind_from_deg < 360):
        raise TerrainSourceError("Invalid wind bearing")
    grid = read_esri_ascii(dem_ascii)
    with Path(road_csv).open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or len(rows) > 100_000:
        raise TerrainSourceError("Empty or excessive road candidate set")
    result = []; missing = 0; seen = set()
    for row in rows:
        ident = row.get("cell_id")
        if not ident or ident in seen:
            raise TerrainSourceError("Duplicate/invalid road cell")
        seen.add(ident)
        x, y = _number(row.get("cell_center_x")), _number(row.get("cell_center_y"))
        if ident != f"utm52n_100m_{math.floor(x/100)}_{math.floor(y/100)}":
            raise TerrainSourceError("Road cell/grid coordinate mismatch")
        if row.get("candidate_source") != "osm_auxiliary":
            raise TerrainSourceError("Unexpected road provenance")
        r = sample_gradient(grid, x, y)
        if r is None:
            missing += 1
            result.append({"cell_id": ident, "status": "UNKNOWN_DEM_COVERAGE"})
            continue
        road_direction = _number(row.get("road_direction_deg"))
        if not 0 <= road_direction < 180:
            raise TerrainSourceError("Invalid road orientation")
        # Wind/road angle is geometry ONLY, not DEM shielding or actual wind.
        cross_road = None
        if wind_from_deg is not None:
            cross_road = abs(math.sin(math.radians(wind_from_deg-road_direction)))
        result.append({"cell_id": ident, "status": "DEM_SOURCE_SAMPLED",
                       "island": row.get("island_name"), "road_direction_deg": road_direction,
                       **r, "wind_cross_road_geometry_proxy": cross_road,
                       "terrain_wind_shielding_verified": False})
    return {
        "schema_version": "habu-100m-road-dem-join-v1",
        "cutoff_time": cutoff.isoformat(),
        "road_sha256": road_sha256, "dem_sha256": dem_sha256,
        "raster_crs": "EPSG:32652",
        "source_type": "osm_auxiliary+actual_dem",
        "coverage_cells": len(result)-missing, "missing_cells": missing,
        "total_cells": len(result),
        "status": "SOURCE_JOIN_PARTIAL" if missing else "STATIC_TERRAIN_JOINED_NOT_MODEL_VALIDATED",
        "provisional": True, "formal_p0_eligible": False,
        "cells": result,
    }
