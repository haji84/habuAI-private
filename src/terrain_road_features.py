from __future__ import annotations

import math

import numpy as np


def road_structure_from_ftcode(ft_code: int) -> str:
    """Decode the structure suffix documented by GSI Vector dataspec.

    For road feature codes at the acquired zoom, suffix 03/13/23/33 is
    bridge/elevated and 04/14/24/34 is tunnel. Other suffixes are not
    reclassified beyond normal/other.
    """
    suffix = int(ft_code) % 100
    if suffix in {3, 13, 23, 33, 43}:
        return "bridge_or_elevated"
    if suffix in {4, 14, 24, 34, 44}:
        return "tunnel"
    return "normal"


def inverse_utm52n(easting: float, northing: float) -> tuple[float, float]:
    a = 6378137.0
    ecc_sq = 0.00669438
    k0 = 0.9996
    x = easting - 500000.0
    y = northing
    lon0 = math.radians(129.0)
    ecc_prime_sq = ecc_sq / (1.0 - ecc_sq)
    m = y / k0
    mu = m / (a * (1.0 - ecc_sq / 4.0 - 3.0 * ecc_sq**2 / 64.0 - 5.0 * ecc_sq**3 / 256.0))
    e1 = (1.0 - math.sqrt(1.0 - ecc_sq)) / (1.0 + math.sqrt(1.0 - ecc_sq))
    j1 = 3.0 * e1 / 2.0 - 27.0 * e1**3 / 32.0
    j2 = 21.0 * e1**2 / 16.0 - 55.0 * e1**4 / 32.0
    j3 = 151.0 * e1**3 / 96.0
    j4 = 1097.0 * e1**4 / 512.0
    fp = mu + j1 * math.sin(2 * mu) + j2 * math.sin(4 * mu) + j3 * math.sin(6 * mu) + j4 * math.sin(8 * mu)
    sin_fp, cos_fp = math.sin(fp), math.cos(fp)
    tan_fp = math.tan(fp)
    c1 = ecc_prime_sq * cos_fp**2
    t1 = tan_fp**2
    n1 = a / math.sqrt(1.0 - ecc_sq * sin_fp**2)
    r1 = a * (1.0 - ecc_sq) / (1.0 - ecc_sq * sin_fp**2) ** 1.5
    d = x / (n1 * k0)
    latitude = fp - (n1 * tan_fp / r1) * (
        d**2 / 2.0
        - (5.0 + 3.0 * t1 + 10.0 * c1 - 4.0 * c1**2 - 9.0 * ecc_prime_sq) * d**4 / 24.0
        + (61.0 + 90.0 * t1 + 298.0 * c1 + 45.0 * t1**2 - 252.0 * ecc_prime_sq - 3.0 * c1**2) * d**6 / 720.0
    )
    longitude = lon0 + (
        d
        - (1.0 + 2.0 * t1 + c1) * d**3 / 6.0
        + (5.0 - 2.0 * c1 + 28.0 * t1 - 3.0 * c1**2 + 8.0 * ecc_prime_sq + 24.0 * t1**2) * d**5 / 120.0
    ) / cos_fp
    return math.degrees(latitude), math.degrees(longitude)


def terrain_stats(values: np.ndarray, spacing_m: float) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or min(array.shape) < 3:
        raise ValueError("terrain array must be a 2-D grid of at least 3x3")
    valid = array[np.isfinite(array)]
    if valid.size == 0:
        return {}
    dz_dy, dz_dx = np.gradient(array, spacing_m, spacing_m)
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
    finite_slope = slope[np.isfinite(slope)]
    cy, cx = array.shape[0] // 2, array.shape[1] // 2
    curvature = (
        array[cy, cx - 1] + array[cy, cx + 1] + array[cy - 1, cx] + array[cy + 1, cx]
        - 4.0 * array[cy, cx]
    ) / spacing_m**2
    aspect = (math.degrees(math.atan2(-dz_dx[cy, cx], -dz_dy[cy, cx])) + 360.0) % 360.0
    return {
        "elevation_min_m": float(np.nanmin(array)),
        "elevation_max_m": float(np.nanmax(array)),
        "elevation_mean_m": float(np.nanmean(array)),
        "elevation_range_m": float(np.nanmax(array) - np.nanmin(array)),
        "slope_mean_deg": float(finite_slope.mean()) if finite_slope.size else float("nan"),
        "slope_max_deg": float(finite_slope.max()) if finite_slope.size else float("nan"),
        "aspect_center_deg": aspect,
        "northness_center": math.cos(math.radians(aspect)),
        "eastness_center": math.sin(math.radians(aspect)),
        "curvature_center": float(curvature),
        "tpi_center_m": float(array[cy, cx] - np.nanmean(array)),
    }


def point_segment_distance_and_bearing(px, py, ax, ay, bx, by) -> tuple[float, float]:
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - ax, py - ay), float("nan")
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    qx, qy = ax + t * dx, ay + t * dy
    distance = math.hypot(px - qx, py - qy)
    bearing = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
    return distance, bearing
