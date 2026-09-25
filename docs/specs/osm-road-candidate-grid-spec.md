# OSM Road Candidate Grid Specification

## Goal

Create an auditable OpenStreetMap auxiliary road universe for Amami Oshima main island and Kakeroma Island, suitable for pre-search prediction freezing without using the evaluation night's GPX.

## Frozen scope

- Included islands: Amami Oshima (`OSM relation 4098976`) and Kakeroma Island (`OSM relation 4098962`).
- Excluded islands: all other islands, including Uke and Yoro.
- Acquisition envelope: WGS84 `(129.10, 27.95, 129.65, 28.55)`.
- Acquisition method: tiled Overpass API queries for every `way["highway"]`, including referenced nodes.
- Raw responses and island-boundary GeoJSON are immutable evidence and retain retrieval timestamp, query, endpoint, byte size, and SHA-256.
- OSM is auxiliary data (`osm_auxiliary`) and must not be represented as official road GIS.
- Attribution: `© OpenStreetMap contributors`, ODbL 1.0.

## Vehicle-route rule

Roads physically described by OSM as vehicle-capable are included in the normal route universe, including forest roads, farm roads, service roads, work roads, and unpaved roads.

- Include normal highway classes: `motorway`, `trunk`, `primary`, `secondary`, `tertiary`, `unclassified`, `residential`, `living_street`, `service`, `track`, and `road`.
- Include other `highway` values only when `motor_vehicle` or `vehicle` is `yes`, `designated`, `permissive`, or `destination`.
- Keep but exclude from normal routing when `motor_vehicle`, `vehicle`, or `access` is explicitly `no` or `private`.
- Do not infer paving, width, legal access, or current physical condition when tags are absent.
- Preserve missingness and explicit access tags for later field correction.

## Processing contract

1. Split the acquisition envelope into deterministic tiles.
2. Save each Overpass response before parsing.
3. Validate JSON and record unsuccessful tiles without pretending coverage.
4. Deduplicate nodes and ways by `(element_type, osm_id)`, preferring the greatest numeric version and rejecting contradictory equal-version payloads.
5. Reconstruct way geometry only from referenced, present nodes; incomplete ways remain audited and are not fabricated.
6. Clip road segments to the union of the two verified OSM island polygons.
7. Classify road type and normal-route eligibility without replacing original tags.
8. Project coordinates to UTM zone 52N and sample each segment densely enough to enumerate intersected 100 m cells.
9. Aggregate static road features per cell and retain contributing OSM way IDs.
10. Keep time expansion separate; a future night's 10-minute rows are generated only for a declared prediction window and stamped with the freeze cutoff.

## Required outputs

- `02_raw_road/osm_overpass_tiles/*.json`
- `02_raw_road/osm_island_boundaries.geojson`
- `02_raw_road/osm_acquisition_manifest.csv`
- `04_processed_road/osm_road_centerlines.geojsonl`
- `04_processed_road/osm_road_candidate_cells.csv`
- `04_processed_road/osm_road_candidate_cells.parquet` when a parquet engine is available; otherwise record `unavailable` without a fake file.
- `04_processed_road/osm_processing_audit.json`
- `07_features/osm_road_feature_definitions.json`
- `12_evidence/osm_road_evidence_manifest.csv`

## Acceptance criteria

- Every configured tile has a manifest row and a terminal status.
- No processed road references an excluded island.
- Duplicate OSM ways appear once in processed centerlines.
- Every normal-route cell has at least one included vehicle-capable road.
- Explicitly prohibited/private roads never set `normal_route=1`.
- Raw and processed files have SHA-256 evidence.
- Unit tests and full project tests pass.

