# OSM Road Candidate Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable OSM road universe for Amami Oshima and Kakeroma, deduplicate and island-clip it, classify vehicle-capable roads, and aggregate them into pre-search 100 m candidate cells.

**Architecture:** A standard-library Python core handles deterministic tiling, Overpass parsing, classification, polygon tests, UTM projection, and cell aggregation. A CLI performs network acquisition with cached immutable raw responses and writes processed outputs plus evidence manifests. Static cells are separated from future-night 10-minute expansion.

**Tech Stack:** Python 3 standard library, existing Habu AI UTM formulas, `unittest`, Overpass JSON, GeoJSON, CSV; optional pandas parquet export only when a parquet engine exists.

**Spec:** `docs/specs/osm-road-candidate-grid-spec.md`

## Global Constraints

- Include Amami Oshima and Kakeroma Island; exclude every other island.
- Include forest, farm, work, service, unpaved, and other vehicle-capable roads in normal routing.
- Never infer missing road surface, width, access, or geometry.
- Preserve raw downloads and SHA-256 evidence.
- Keep OSM auxiliary provenance separate from official GSI road data.
- Do not use evaluation-night GPX to create the pre-search candidate universe.

## Review Focus

- A way crossing tile boundaries is emitted once after deduplication.
- A way with a missing referenced node is audited and never joined across the gap.
- Explicit `access=private/no` or `motor_vehicle=no` overrides a vehicle-like highway class.
- Roads on Uke/Yoro or bbox sea space do not create candidate cells.
- A segment lying exactly on a 100 m boundary does not silently disappear.

---

### Task 1: Tiling, parsing, deduplication, and classification

**Files:**
- Create: `src/osm_road.py`
- Create: `tests/test_osm_road.py`

**Interfaces:**
- Produces: `build_bbox_tiles`, `parse_overpass_elements`, `deduplicate_elements`, `classify_vehicle_route`, `reconstruct_way_parts`.

- [ ] **Step 1: Write failing tests** for deterministic tiling, higher-version deduplication, contradictory equal-version rejection, missing-node part breaks, and access overrides.
- [ ] **Step 2: Run** `python -m unittest tests.test_osm_road -v` and verify failures are missing-interface failures.
- [ ] **Step 3: Implement minimal pure-Python functions** with original OSM tags preserved.
- [ ] **Step 4: Run** `python -m unittest tests.test_osm_road -v` and verify all Task 1 tests pass.

### Task 2: Island clipping and 100 m aggregation

**Files:**
- Modify: `src/osm_road.py`
- Modify: `tests/test_osm_road.py`

**Interfaces:**
- Consumes: reconstructed WGS84 way parts and classification records from Task 1.
- Produces: `load_target_polygons`, `point_in_multipolygon`, `clip_parts_to_target`, `road_cells_100m`, `aggregate_road_cells`.

- [ ] **Step 1: Write failing tests** using hand-built island polygons for included/excluded segments, holes, boundary segments, and literal expected 100 m cell IDs.
- [ ] **Step 2: Run** the focused test module and verify the new behavior fails.
- [ ] **Step 3: Implement polygon membership, segment densification, UTM52N projection, and aggregation.**
- [ ] **Step 4: Run** the focused tests and verify all pass.

### Task 3: Auditable acquisition and processing CLI

**Files:**
- Create: `scripts/fetch_osm_road.py`
- Create: `tests/test_fetch_osm_road.py`
- Modify: `src/public_data.py`

**Interfaces:**
- Consumes: Task 1 and Task 2 functions.
- Produces: raw tile JSON, boundary GeoJSON, acquisition manifest, centerline GeoJSONL, candidate-cell CSV/optional Parquet, processing audit, definitions, evidence manifest.

- [ ] **Step 1: Write failing CLI tests** against local fixture responses, including cached rerun, failed tile manifesting, SHA calculation, and no-Parquet status.
- [ ] **Step 2: Run** `python -m unittest tests.test_fetch_osm_road -v` and verify missing CLI behavior fails.
- [ ] **Step 3: Implement acquisition and processing with GET requests, bounded retries, sequential requests, and immutable raw caching.**
- [ ] **Step 4: Run** CLI tests and verify all pass.

### Task 4: Real acquisition, audits, integration contract, and documentation

**Files:**
- Modify: `README.md`
- Create/update all output files required by the specification.

**Interfaces:**
- Consumes: live Overpass and Nominatim data, CLI from Task 3.
- Produces: complete OSM candidate-grid artifacts and a documented pre-search input contract.

- [ ] **Step 1: Run the CLI** for all deterministic tiles and both verified island relations.
- [ ] **Step 2: Verify terminal tile coverage, feature counts, island exclusions, normal-route counts, hashes, and optional Parquet status.**
- [ ] **Step 3: Add README commands, provenance, limitations, and the pre-search freeze usage contract.**
- [ ] **Step 4: Run** `python -m unittest discover -s tests -v` and a separate artifact-audit command; require zero failures before reporting completion.

