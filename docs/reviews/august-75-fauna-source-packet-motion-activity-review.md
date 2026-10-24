# 75 fauna-source evidence packets: local actual-GPX motion versus unproven Habu search

## Scientific decision target
The 75 high-priority review packets contain 99 original text-backed sightings anchored to 94 unique 100m x 10min candidate cells, with strict real-GPX/OSM proximity and paired nightly session markers (PR #83). Their sightings prove that the log recorded an observation at a point; they do not by themselves prove scanning the entire surrounding road, or that Habu were absent.

**This slice distinguishes local vehicle motion context, never certifies active Habu searching.** The separate all-owner-captures-complete and canonical individual ID requirements still block model labels.

## Bounded actual-source motion review
1. Recompute the 705 sighting-to-GPX audit and the original 774 review-group membership. Fail if the 75 groups, 94 candidate cells, 99 strict sightings or any source hash/OSM archive identity changed.
2. For each of the 99 strict original sighting timestamps, read existing original GPX of that night, verify the independent GPX SHA256, point count and 07:00 JST boundary. Reject excluded spikes, segment-break points and unknown/HDOP >10 measurements for local speed-context assertions.
3. In a bounded ±90-second window and 100-m radius of that exact source sighting coordinate, retain only actual GPS fixes unambiguously matching the SAME auxiliary OSM way as the recorded original source. No lines or coordinates are interpolated between points.
4. Count actual selected GPS points, valid source speed readings, low-speed (0.5–6 m/s), stopped (<0.5 m/s), higher-speed transit candidate (>=11 m/s), and real adjacent measured point-pair seconds with <=5s GPS gaps. A source sighting at motion speed is possible; a speed category cannot erase the encounter.
5. Count timestamp-separated GPS fix clusters in the ORIGINAL 100m source cell, but explicitly do NOT interpret clusters as proven distinct driven passes or deliberate repeat search.
6. Classify local evidence `LOW_SPEED_MOVEMENT_NEAR_LOGGED_FAUNA`, `STATIONARY_NEAR_LOGGED_FAUNA`, `FAST_PASSAGE_NEAR_LOGGED_FAUNA`, `MIXED_MOVEMENT_NEAR_LOGGED_FAUNA`, or `INSUFFICIENT_CONTIGUOUS_GPX_MOTION`.
7. Group observations back to the same 75 original packet IDs, with explicit status for packets with competing fast-travel context, packets with local low/stopped context, or those with insufficient/ambiguous motion. These are review priority and not scientifically verified search activities.

## Source authenticity and strict bans
- August raw Habu Library TXT is byte-verified, has 46 capture event statements and a monthly owner-confirmed capture total of 47 (not 47 fully independent canonical specimen IDs). Current through-October20 capture count remains 243.
- September-25 OSM archive is auxiliary post-hoc data, never a retrospective August P0 road universe.
- Existing 3,491 no-capture *review candidates* and 774 packets are not rewritten or relabeled. None of these are a formally eligible Negative. The 75 selected packets remain a priority subset.
- A source-logged sighting is positive evidence for the particular recorded animal's observation, NOT a verified Habu capture, whole-road active search, capture denominator or confirmed absence.
- Every reviewed group remains `HUMAN_OR_INDEPENDENT_EVIDENCE_REQUIRED`; full-road search=false; outcome ledger complete=false; formal Positive=0, Negative=0. No `model_learning.json` or original P0 is created.

## Evidence outputs
`scripts/audit_august_75_fauna_motion_review.py` writes `aggregate.json` with only counts, class histograms, nights and hashed group IDs, plus **private Actions-only** 75-group and 99-source-anchor JSONs holding exact timestamps/coordinates/OSM way IDs. The private artifact is retained for 7 days. Aggregate receipt can be preserved in the repository once CI succeeds. Do not commit detailed GPS/organism timestamps or positions to dashboard.

## Accept/reject
Accept the diagnostic only when exact original source and GPX/OSM binding passes, exactly 75/99/94 are retained, motion classifications account for all events/groups once, synthetic speed/gap/revisit tests pass, and all official model labels remain unknown. If missing owner search-vs-transit evidence, scientifically certifiable Habu search segments remain **zero**, whatever the motion heuristic says.
