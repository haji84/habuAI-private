# 2026 August fauna sighting source × GPX × OSM auxiliary road evidence audit

## Scientific role
The user field log's explicitly recorded `目撃` entries are location/time/source evidence of **animals observed**, not proof that the surrounding 100m road zone was completely searched. Frogs, birds, rodents and other snakes are habitat/activity context, **not evidence of the presence or absence of Habu**. Himehabu (`ヒメハブ`) is kept distinct from Habu (`ハブ`). Roadkills (`轢死`) and personally captured Habu (`捕獲`) are separate record families; no other-species sightings are added to owner capture count.

## Original data and verified scope
- Source: 116,496-byte/10,506-line native user Library Habu TXT, SHA-256 `130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`. Independently original-byte matched on 2026-10-24 in PR #82.
- Raw August original: 915 distinct `目撃` source events across all August nights; 704 of those belong to the 12 operational nights with original GPX. An August night without actual GPX cannot be assigned an invented GPS position.
- Additional distinct `轢死` reactions in the 12 GPX nights: 11, including 3 explicitly recorded Habu roadkills. Roadkill is not a capture, and the 3 records are not automatically original live sightings.
- Among 704 `目撃` source blocks for the 12 nights, 9 have exact source category `ヒメハブ`, zero are exact `ハブ`, and 695 have other fauna classifications. This describes only **the explicitly recorded source categories**, not the actual field biology census.
- One `目撃` record has no uniquely parsed original coordinate pair. Do not borrow another event's GPS coordinates or interpolate a route.
- Owner-confirmed August personal Habu capture total remains 47, with 46 capture statements across 17 capture nights. Sightings and roadkills never change this figure.

## Exact evidence-binding algorithm
1. Reuse the existing raw-Habu log `index_events` parser and exact source-block SHA/line number; accept only explicit `目撃` for fauna sightings. Keep the native organism note, quantity literal and timestamp unchanged. Other-person capture notes and roadkills never become normal sightings.
2. For each of 12 archived GPX nights, independently SHA-check original GPX against the existing QC inventory, use actual GPX points only, omit anomaly-spike points and HDOP>10, and preserve HDOP-missing uncertainty.
3. Compare source event GPS coordinates to **observed** valid GPS points within ±10 minutes and 100 metres; store the best real source point and offset. A tighter retrospective association requires distance ≤35 metres, time difference ≤90 seconds and a known acceptable HDOP. Missing coordinates/weak fixes remain missing/weak, not invented.
4. Match both original sighting coordinate and actual nearest GPX point independently to September 25 OSM auxiliary centerlines (35-metre rule). Only accept same-way association when both OSM matches are unambiguous and have identical OSM way IDs. OSM is a post-hoc research layer, not an August 2026 P0 pre-exploration road universe.
5. Match the **original sighting coordinate and original sighting time bin**, not just the nearest GPS sample, to PR #80/#81's pre-existing 3,491 review-only noncapture sampled cells. For a stronger *review priority marker*, require same original 100m×10min cell as actual GPS point, strict source↔GPX proximity, same unambiguous OSM way, matching source candidate OSM way, and explicitly paired search-session marker. This still does NOT prove active 100m-road search.
6. Attach exact source sighting-block SHA to the existing PR #82 review group ID. Groups are the earlier 774 spatial/time/way review packets, not reconstructed continuous travel routes. Avoid double counting multiple sightings in the same candidate cell.
7. Every event stays `observation=UNKNOWN`, `training_label=null`, `confirmed_search_effort_for_entire_road_segment=false`, and `capture_outcome_ledger_complete=false`. No Negative, Positive or model learning snapshot can be promoted from sighting-only evidence.

## Provenance and privacy
- The private Actions artifact (7-day retention) contains source event time/coordinates/OSM way, GPS association, and per-review-packet source-block IDs. This is for scientific review, not for public release.
- The permanent aggregate report contains only per-night counts and organism note totals. It does not publish exact private sightings or capture coordinates or infer new animals from environmental notes.
- Output source-based biological correlations may eventually inform research feature selection after pre-cutoff availability review; they must not be retroactively inserted into an old prediction Freeze.

## Acceptance conditions
- 704 unique original fauna-sighting source blocks on 12 real-GPX nights, 915 original sightings across August, 11 roadkill reactions kept separate, 9 Himehabu distinct from Habu.
- Honest handling of a sighting missing native coordinate, weak/absent GPX, HDOP gaps, OSM road ambiguity, and missing start/end markers on Aug 12/13/29.
- Accurate per-night unique source matches and association to existing noncapture candidate cells/groups, with no new false road-search certification.
- CI full-suite and private evidence E2E. Formal science Positive=0, Negative=0, and August captures=47, season through 2026-10-20=243 are invariant.
