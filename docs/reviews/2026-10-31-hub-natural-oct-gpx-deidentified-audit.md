# HUB NATURAL 2026-10-31 October log + GPX intake: de-identified verification

## Sources and privacy
- User supplied one October field log, source SHA-256: `d4c458671defa1b6a6a4dac5a9d1733162c23c80685cef553a13ae24a2fe9b3e`.
- **14 original GPX** files, **14 unique SHA-256**, **236,663 track points**, **13 distinct operational nights** (Asia/Tokyo 07:00 boundary).
- This file intentionally contains **no coordinates, street names, capture spots, tracks, device identifiers, or original GPX bytes**. Full originals remain in conversation attachments, not uploaded by this change to the public GitHub repository.

## Personal Habu captures vs existing dashboard

| Operational night | Owner capture count from uploaded log | Existing frozen baseline (main, through Oct20) | Owner effort overlay PR #136 | Added to 4 post-overlay nightly files |
| --- | ---: | --- | --- | ---: |
| Oct06 | 0 | 0 | no change | 0 |
| Oct08 | 0 | 0 | no change | 0 |
| Oct14 | 3 | 3 | no change | 0 |
| Oct15 | 3 | 3 | no change | 0 |
| Oct16 | 7 | 7 | no change | 0 |
| Oct18 | 2 | 2 | no change | 0 |
| Oct20 | 2 | 2 | no change | 0 |
| Oct22 | 2 | after baseline | 2 | 0 |
| Oct24 | 4 | after baseline | 4 | 0 |
| Oct26 | 3 | after baseline | after overlay | **3** |
| Oct28 | 2 | after baseline | after overlay | **2** |
| Oct29 | 2 | after baseline | after overlay | **2** |
| Oct30 | 6 | after baseline | after overlay | **6** |

Uploaded field log **36 personal Habu capture events** = 17 in main baseline + 6 in PR #136 owner effort overlay + **13** previously unregistered nights. No sightings, roadkill, other people's catches, or Himehabu included in capture total. Do not re-add earlier source families.

- main frozen count through Oct20: **243** (April currently 10; owner's earlier eleven-claim not resolved by these October files).
- PR #136 through Oct24: **249**, including Oct22 = 2 and Oct24 = 4, no extra copies.
- Four new owner night tallies: **13**, for a **provisional 262 personal captures through Oct30**, October count **36**.
- Personal effort for that PR: 97 through Oct24 + four observed positive nights = **101**; science-quality Negative/Exposure is **not** established by this arithmetic.

## GPS cross-match results and limitations
- 35 of 36 October capture events have a recorded GPX point within **100m** and within **5 minutes** of the owner's capture timestamp; the comparison uses the original GPS coordinate and time privately and only aggregates success counts here.
- **Oct24 20:27** is outside both available GPX segments. GPX records end around 19:26:55 and resume around 20:34:29, an approximately **67min34sec gap**. Owner's capture count remains 4; scientific point-level GPS match stays **unverified**, not fabricated or interpolated. This is consistent with existing Oct24 PR #92/#147 source evidence.
- Every GPX file parsed with no XML errors, zero duplicate SHA-256, and all track samples carried UTC timestamps converted to JST. All matching is observational, **not** formal proof of capture identity, 100m × ±10min prediction accuracy, exploration negatives, or P0 model performance.
- Because this repository is Public, **never commit the log, raw GPX, per-event coordinates, or precise route segments** to this PR. Existing Public repo raw GPS exposure must be handled separately.

## Release contract
- Changes extend the **existing Draft PR #136** only, not a new PR.
- Source `dashboard/owner_effort_2026-10-26.json` stays frozen at 249 captures / 97 effort nights *through Oct24*; later dates are separate replacement-style owner nightly aggregate records.
- No main merge, production deployment, PDCA scoring, or model promotion until PR latest-head CI, independent review, compatibility with PR #92 and security checks pass.
- If a canonical original event log for Oct26–30 arrives, counts must reconcile exactly rather than increment the owner tally again.
