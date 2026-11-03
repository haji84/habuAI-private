# October 2026 Habu observational audit (four operational nights)

Status: INDEPENDENT_LOCAL_EVIDENCE_VERIFIED / NOT_OFFICIAL_PREDICTION_SCORING

Operational-night rule: Asia/Tokyo, events before 07:00 belong to the preceding night.

This audit independently re-reads the four original GPX attachments and verifies raw SHA-256 against the evidence manifests staged in this PR. All four exact original SHA-256 hashes match. This audit is not a 100m ±10min **prediction** validation because no eligible historical ORIGINAL P0/P1 freeze exists for these nights.

| Night | Trackpoints | Time (JST) | SHA match | Owner captures | Habu roadkill reaction |
| --- | ---: | --- | --- | ---: | ---: |
| 2026-10-06 | 8,528 | 18:59:27 to 21:22:49 | PASS | 0 | 0 |
| 2026-10-08 | 9,143 | 19:13:01 to 21:45:26 | PASS | 0 | 1 |
| 2026-10-14 | 20,481 | 19:02:54 to 00:52:30 next day | PASS | 3 | 0 |
| 2026-10-15 | 18,610 | 18:31:56 to 23:42:22 | PASS | 3 | 0 |

Total: 56,762 GPX points, six owner captures and one additional Habu roadkill observation. The roadkill is an occurrence reaction, **never** owner capture.

## Spatial and time audit

Every one of the seven user-logged Habu events has at least one GPX point within 100m spatial distance and ±10 minutes of the recorded event time.

This supports coherence of logged observations and track evidence; it does **not** demonstrate that any issued forecast correctly predicted a 100m/time target.

## Auxiliary observed-exposure diagnostic

On a separate local WGS84 -> UTM zone 52N calculation, positions observed in 100m projected cells and ten-minute clock bins yield:

| Night | Distinct visited spatial/time grid units |
| --- | ---: |
| 2026-10-06 | 427 |
| 2026-10-08 | 476 |
| 2026-10-14 | 1,457 |
| 2026-10-15 | 945 |

These 3,305 observed units are a **diagnostic GPS coverage count**, not a road-matched/canonical Negative dataset. GPS jump and route geometry processing, capture-unit reconciliation at time-bin boundaries, actual visibility/detection and repeated visits require the production road-GIS exposure contract before using them for model training or official scoring.

Distance estimates depend on coordinate projection and GPS-jump filtering; they must not be silently substituted for prior distance figures. A separate local calculation projected to EPSG:32652 and discarded nonpositive-time and >130km/h steps, yielding 33.43/37.57/113.37/75.71km respectively. These are method-specific *diagnostics*, not certified odometer distances.

## Forecast provenance and scientific status

The contemporaneous P0/P1 original freeze for these four nights is unavailable.

- 10/06: provisional point forecast was withdrawn before exploration.
- 10/08: prediction request recorded but numerical issuance was not recovered.
- 10/14: approximate provisional forecast is later than the GPX start, not eligible as P0.
- 10/15: recovered provisional timestamp is too close to or after GPX start to establish a pre-exploration P0.

Recovery candidates live in evidence/prediction_recovery_candidates/ only. They must never be written into predictions/original/ or counted as official performance.

Therefore: formal P0, realtime P1+, Stage1 1km Top10 Recall, formal 100m ±10min KPI, calibration and candidate Champion promotion are BLOCKED by forecast lineage evidence, independent of this raw-data audit.

## Integration status

Data and integrity tests are staged in PR #39. Do not merge while repository Actions jobs fail before any runner step (Issue #40); do not bypass CI, soften scientific gates, or treat missing CI as PASS. The independent local raw-file audit validates attachment identity, not GitHub Actions execution.
