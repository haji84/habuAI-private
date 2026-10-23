# GSI DEM two-island source probe (research only)

The CLI `python scripts/gsi_dem_source_probe.py` requests actual GSI DEM elevation PNG tiles at two **public, fixed inland sampling areas** of Amami-Oshima and Kakeroma, with a bounded fallback between DEM10B and DEM5A/5B. It saves the exact returned PNG bytes and SHA-256, URL, tile XYZ, received timestamp, and coverage statistics. The input coordinates are *not* private personal capture sites.

The elevation RGB decoder uses the GSI official 24-bit signed scheme (RGB 128,0,0 is NODATA; 0.01m quantization). Reference: https://cyberjapandata.gsi.go.jp/development/demtile.html. A genuine HTTP acceptance run is executed by `.github/workflows/live-gsi-dem-e2e.yml` on this PR and stores a 30-day GitHub artifact.

**Important limits:** These are only two PNG tiles to prove internet access, exact source archiving and DEM decoder validity. It is **not** complete terrain coverage over all 16,990 road cells. Source pixel elevations are in a Web Mercator tile addressing scheme; the existing `road_dem_join.py` requires true UTM52N projected ASCII data, so one must not rewrite the tile's CRS label to trick the join. Full source-preserving reprojection/resampling and coverage/QC remain required, as does actual terrain-wind shielding. Model training and production P0 remain blocked.

The free tile service is subject to GSI's published rules and must not be mass-scraped irresponsibly. Any island-wide conversion must use an approved acquisition plan and maintain source provenance.
