#!/usr/bin/env python3
"""Bounded live GSI DEM PNG source proof for both islands, NOT an island-wide DEM.

Retains PNG bytes, hash, retrieval time, valid elevation pixels and source layer.
No forecast issuance, no GPS/capture data, no road-cell interpolation.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
# Public reference-area sampling points, unrelated to personal capture locations.
SITES = (
    ("amami_inland_source_probe", "奄美大島", 28.333, 129.460),
    ("kakeroma_inland_source_probe", "加計呂麻島", 28.138, 129.297),
)
LAYERS = (("dem_png", 14), ("dem5a_png", 15), ("dem5b_png", 15))
BASE = "https://cyberjapandata.gsi.go.jp/xyz"
MAX_TILE_BYTES = 600_000


class DemProbeError(ValueError):
    pass


def tile(lat, lon, z):
    if not (-85.05 < lat < 85.05 and -180 <= lon <= 180 and 1 <= z <= 18):
        raise DemProbeError("Invalid geographic position or zoom")
    n = 2 ** z
    tx = (lon + 180.0) / 360.0 * n
    ty = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return int(tx), int(ty), int((tx % 1)*256), int((ty % 1)*256)


def decode_rgb(rgb):
    red, green, blue = tuple(rgb[:3])
    x = (red << 16) + (green << 8) + blue
    if x == 2**23:
        return None
    return ((x if x < 2**23 else x-2**24) * 0.01)


def validate_png(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_TILE_BYTES:
        raise DemProbeError("Empty or oversized GSI PNG")
    try:
        with Image.open(io.BytesIO(raw)) as picture:
            if picture.format != "PNG" or picture.size != (256, 256):
                raise DemProbeError("GSI must return a 256x256 elevation PNG")
            pic = picture.convert("RGB")
            values = [decode_rgb(pixel) for pixel in pic.getdata()]
    except (OSError, ValueError) as exc:
        raise DemProbeError("Invalid DEM PNG") from exc
    valid = [v for v in values if v is not None]
    if not valid:
        raise DemProbeError("No valid altitude in GSI tile")
    return {"valid_pixels":len(valid),"nodata_pixels":len(values)-len(valid),
            "elevation_min_m":round(min(valid),2),"elevation_max_m":round(max(valid),2)}


def _download(url):
    if not url.startswith(BASE + "/"):
        raise DemProbeError("Unapproved DEM URL")
    with urlopen(Request(url, headers={"User-Agent":"Habu-AI-scientific-source-probe/1.0"}),
                 timeout=15) as response:
        if response.status != 200:
            raise DemProbeError("Unexpected GSI HTTP status")
        body = response.read(MAX_TILE_BYTES+1)
    if len(body) > MAX_TILE_BYTES:
        raise DemProbeError("Oversized GSI response")
    return body


def acquire(root=ROOT, *, downloader=None, clock=None):
    root = Path(root).resolve()
    downloader = downloader or _download
    clock = clock or (lambda: datetime.now(timezone.utc))
    out=[]
    for ident, island, lat, lon in SITES:
        failures=[]
        selected=None
        for layer, z in LAYERS:
            x,y,px,py=tile(lat,lon,z)
            url=f"{BASE}/{layer}/{z}/{x}/{y}.png"
            try:
                raw=downloader(url)
                metrics=validate_png(raw)
                selected=(layer,z,x,y,px,py,url,raw,metrics)
                break
            except (HTTPError, URLError, DemProbeError, OSError) as exc:
                failures.append(f"{layer}:{type(exc).__name__}")
        if selected is None:
            raise DemProbeError(f"No valid DEM tile for {island}: {','.join(failures)}")
        layer,z,x,y,px,py,url,raw,metrics=selected
        acquired=clock()
        if acquired.tzinfo is None or acquired.utcoffset() is None:
            raise DemProbeError("Clock must be timezone aware")
        sha=hashlib.sha256(raw).hexdigest()
        name=f"{ident}-{layer}-{z}-{x}-{y}-{sha[:16]}.png"
        directory=root/"evidence"/"gis"/"gsi-dem-source-probe"
        directory.mkdir(parents=True,exist_ok=True)
        destination=directory/name
        with destination.open("xb") as output:
            output.write(raw);output.flush();os.fsync(output.fileno())
        if hashlib.sha256(destination.read_bytes()).hexdigest()!=sha:
            raise DemProbeError("Archived PNG differs from retrieved bytes")
        out.append({"site_id":ident,"island":island,"reference_point_lat_lon":[lat,lon],
                    "source":url,"layer":layer,"zxy":[z,x,y],"reference_pixel":[px,py],
                    "raw_sha256":sha,"received_at_utc":acquired.astimezone(timezone.utc).isoformat(),
                    "relative_path":destination.relative_to(root).as_posix(),
                    **metrics})
    return {"schema_version":"habu-gsi-dem-source-probe-v1",
            "status":"TWO_ISLAND_DEM_TILES_ARCHIVED_NOT_FULL_COVERAGE",
            "provider":"Geospatial Information Authority of Japan",
            "source_spec":"https://cyberjapandata.gsi.go.jp/development/demtile.html",
            "samples":out,
            "full_road_cell_coverage":False,"terrain_wind_shielding_verified":False,
            "official_original_p0_issued":False}


def main():
    try:
        result=acquire()
        path=ROOT/"artifacts"/"gsi-dem-probe"/"receipt.json"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    except (DemProbeError, OSError, ValueError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2
    print(json.dumps(result,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
