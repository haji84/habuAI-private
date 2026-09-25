from __future__ import annotations

from datetime import datetime, timezone


# Conservative rectangle that contains Amami-Oshima main island. Extra sea and
# neighbouring-island pixels are retained in raw tiles and excluded downstream.
AMAMI_MAIN_ISLAND_BBOX = (129.10, 27.95, 129.65, 28.55)

PUBLIC_SOURCES = (
    {
        "data_id": "DEM5A",
        "name": "標高タイル DEM5A (PNG)",
        "provider": "国土地理院",
        "url_template": "https://cyberjapandata.gsi.go.jp/xyz/dem5a_png/{z}/{x}/{y}.png",
        "resolution": "約5m; z15",
        "crs": "Web Mercator tile / source heights in metres",
        "vertical_datum": "基盤地図情報数値標高モデル準拠",
        "official": True,
    },
    {
        "data_id": "DEM5B",
        "name": "標高タイル DEM5B (PNG)",
        "provider": "国土地理院",
        "url_template": "https://cyberjapandata.gsi.go.jp/xyz/dem5b_png/{z}/{x}/{y}.png",
        "resolution": "約5m; z15",
        "crs": "Web Mercator tile / source heights in metres",
        "vertical_datum": "基盤地図情報数値標高モデル準拠",
        "official": True,
    },
    {
        "data_id": "DEM5C",
        "name": "標高タイル DEM5C (PNG)",
        "provider": "国土地理院",
        "url_template": "https://cyberjapandata.gsi.go.jp/xyz/dem5c_png/{z}/{x}/{y}.png",
        "resolution": "約5m; z15",
        "crs": "Web Mercator tile / source heights in metres",
        "vertical_datum": "基盤地図情報数値標高モデル準拠",
        "official": True,
    },
    {
        "data_id": "DEM10B",
        "name": "標高タイル DEM10B (PNG)",
        "provider": "国土地理院",
        "url_template": "https://cyberjapandata.gsi.go.jp/xyz/dem_png/{z}/{x}/{y}.png",
        "resolution": "約10m; z14",
        "crs": "Web Mercator tile / source heights in metres",
        "vertical_datum": "基盤地図情報数値標高モデル準拠",
        "official": True,
    },
    {
        "data_id": "GSI_RDCL",
        "name": "地理院地図Vector道路レイヤ（PBFタイル）",
        "provider": "国土地理院",
        "url_template": "https://cyberjapandata.gsi.go.jp/xyz/experimental_bvmap/{z}/{x}/{y}.pbf",
        "resolution": "z16",
        "crs": "Web Mercator vector tile; decoded to longitude/latitude",
        "vertical_datum": "not applicable",
        "official": True,
    },
    {
        "data_id": "OSM_ROAD_AUX",
        "name": "OpenStreetMap道路データ（補助）",
        "provider": "OpenStreetMap contributors",
        "url_template": "https://overpass-api.de/api/interpreter?data={z}{x}{y}",
        "resolution": "vector ways and nodes; tiled query",
        "crs": "WGS84 geographic coordinates; processed to UTM zone 52N",
        "vertical_datum": "not applicable",
        "official": False,
    },
)


def validate_source_catalog(rows=PUBLIC_SOURCES) -> list[str]:
    required = {
        "data_id", "name", "provider", "url_template", "resolution",
        "crs", "vertical_datum", "official",
    }
    errors: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        missing = sorted(required - set(row))
        if missing:
            errors.append(f"row {index}: missing {','.join(missing)}")
        data_id = str(row.get("data_id", ""))
        if data_id in seen:
            errors.append(f"row {index}: duplicate data_id {data_id}")
        seen.add(data_id)
        template = str(row.get("url_template", ""))
        if not all(token in template for token in ("{z}", "{x}", "{y}")):
            errors.append(f"row {index}: invalid tile template")
    return errors


def acquisition_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
