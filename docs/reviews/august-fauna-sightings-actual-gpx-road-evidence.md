# 2026 August fauna sighting source × GPX × OSM auxiliary road evidence audit

## Scientific role
The user field log's explicitly recorded `目撃` entries are location/time/source evidence of **animals observed**, not proof that the surrounding 100m road zone was completely searched. Frogs, birds, rodents and other snakes are habitat/activity context, **not evidence of the presence or absence of Habu**. Himehabu (`ヒメハブ`) is kept distinct from Habu (`ハブ`). Roadkills (`轢死`) and personally captured Habu (`捕獲`) are separate record families; no other-species sightings are added to owner capture count.

## Original data and verified scope
- Source: 116,496-byte/10,506-line native user Library Habu TXT, SHA-256 `130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c`. Independently original-byte matched on 2026-10-24 in PR #82.
- Raw August original: 915 ordinary timestamp-delimited `目撃` blocks, plus one verifiably embedded second sighting inside an Aug21 compound block, giving **916 distinct original timestamped sightings** across August. The 12 actual-GPX nights contain **704 ordinary blocks / 705 recovered source sightings**. An August night without actual GPX cannot be assigned an invented GPS position.
- Additional distinct `轢死` reactions in the 12 GPX nights: 11, including 3 explicitly recorded Habu roadkills. Roadkill is not a capture, and the 3 records are not automatically original live sightings.
- Among 704 `目撃` source blocks for the 12 nights, 9 have exact source category `ヒメハブ`, zero are exact `ハブ`, and 695 have other fauna classifications. This describes only **the explicitly recorded source categories**, not the actual field biology census.
- One Aug21 source block originally appeared to have no unique coordinate pair because two `目撃` events were pasted together: `2026/08/22 1:03` and a line beginning `あ2026/08/22 1:07`. The latter has its own literal `目撃` marker, quantity, organism note and GPS coordinates. Split exactly these two source byte spans in a **derived-only** record, with source parent SHA and original line offsets retained. Never modify native TXT, silently discard either sighting or recover chat-comment timestamps such as `なう(2026/...)`.
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
- 705 original timestamped fauna-sighting records recovered from 704 ordinary source blocks on 12 real-GPX nights; 916 original sightings across August including the verified one compound split, 11 roadkill reactions kept separate, 9 Himehabu distinct from Habu.
- Honest handling of a sighting missing native coordinate, weak/absent GPX, HDOP gaps, OSM road ambiguity, and missing start/end markers on Aug 12/13/29.
- Accurate per-night unique source matches and association to existing noncapture candidate cells/groups, with no new false road-search certification.
- CI full-suite and private evidence E2E. Formal science Positive=0, Negative=0, and August captures=47, season through 2026-10-20=243 are invariant.

## Source-block parsing correction

The raw TXT is unchanged and byte-identical to the owner-uploaded original. The base date-line parser found 704 GPX-night sighting blocks. Within one Aug21 block it found two separately timestamped `目撃` records separated by stray text `あ`, each with independent original location. A derived-only strict split restores **705** candidate sightings on the 12 GPX nights. The 915 plain sighting blocks across all August similarly become 916 original sightings. The correction changes observation event accounting only; it does not change 47 personal captured Habu or 3,491 noncapture-review candidate cells, and creates no scientific Positive/Negative training labels.

## Actual full-source CI results (2026-10-24)

Source-run evidence: https://github.com/haji84/habuAI-private/actions/runs/40067959807 . The restored 705 actual `目撃` source events have **705/705 GPX proximity matches within 100m and ±10min**, but this is a broad source-correspondence screen, not 705 proven road-search observations. Stricter ≤35m/≤90sec and known-HDOP proximity: **222**. Separately, **639** observation+GPX points are near the same unambiguous OSM auxiliary centerline (do not conflate this with the stricter 222 subset). **94 distinct preexisting noncapture review cells** have stricter sighting+GPS+OSM+paired-session corroboration, covering **75 of 774** existing review packets. These correspond to **99 sighting event anchors**, since some cells contain multiple observations. The original 3,491 candidate review cells are not increased or relabeled.

| Operational night | Original sighting records | GPX matched | Strict GPS anchor | Same OSM way | Strict observation anchored in review candidate (events) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 8/12 | 53 | 53 | 18 | 48 | 0 |
| 8/13 | 35 | 35 | 6 | 34 | 0 |
| 8/15 | 58 | 58 | 12 | 52 | 6 |
| 8/17 | 34 | 34 | 15 | 29 | 5 |
| 8/19 | 52 | 52 | 24 | 48 | 16 |
| 8/21 | 55 | 55 | 24 | 47 | 9 |
| 8/23 | 73 | 73 | 22 | 67 | 17 |
| 8/24 | 76 | 76 | 18 | 70 | 5 |
| 8/27 | 73 | 73 | 25 | 68 | 16 |
| 8/28 | 113 | 113 | 34 | 102 | 20 |
| 8/29 | 40 | 40 | 16 | 35 | 0 |
| 8/31 | 43 | 43 | 8 | 39 | 5 |
| **Total** | **705** | **705** | **222** | **639** | **99 (94 distinct cells)** |

One Aug21 malformed source line causes raw date-line parser to merge two events. The corrected source split is auditable via the full source-byte SHA, original parent block SHA and distinct source subspan SHA. Original TXT bytes are left untouched. There are **916 native recorded August sightings overall**, of which 705 belong to these twelve GPX nights. Nine of 705 are Himehabu, not Habu. There are zero explicitly category=`ハブ` direct sightings in the 705, but **three separate original Habu `轢死` source reactions** in the 11 roadkill reactions. Absence of Habu sighting entries is not proof of absent Habu.

Persistent aggregate-only receipt: `evidence/recovered_sources/2026-08-fauna-gpx-road-sighting-ci-receipt.json`. Detailed original source coordinate/time/OSM individual-event files remain in private 7-day Actions artifact. Formal Positive=0, Negative=0; full segment search and all-capture completeness remain unauthenticated.
