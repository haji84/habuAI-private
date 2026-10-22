# Four-night GPX moving-search / stop-candidate audit

Date of analysis: 2026-10-22 (JST)  
Scope: existing original GPX data for 2026-10-06 / 08 / 14 / 15, staged in this PR.  
Qualification: **EXPLORATORY_SOURCE_VERIFIED; NOT NEGATIVE CERTIFICATION, NOT REST VERIFICATION, NOT FORECAST ACCURACY.**

## Owner methodology and interpretation

Owner reports: GPX tracking is **basically continuous Habu search**; prolonged stops sometimes represent breaks. All Habu personally caught during exploration are logged, including zero-capture nights (self-report). These statements do **not** say every stop is a break or certify every second of GPS coverage as an actively observed road section. Captures, sightings, another person's captures and roadkills remain separate source classes.

To avoid assuming any unprovided break threshold, this study uses a **candidate detection sensitivity rule**, not a claim about actual rest: consecutive source-recorded GPS speed at most **0.8 m/s**, within **30 m** of the candidate's first point, with no interpoint timestamp gap over **20 s**. Only groups lasting **120 s or more** are shown. A separate sensitivity count is provided for **300 s** and **600 s**. A close owner capture or Habu reaction (anchor within 100 m and event within ten minutes of the stationary group) **protects** the stop against automatic rest classification. Unmatched groups remain **UNKNOWN_STOP_PURPOSE**, never confirmed rest.

## Source integrity and measured results

The actual GPX UTF-8 bytes were reconstructed from their **Git object blobs** (for the Oct 14/15 line archives, joined in manifest order with the original LF separators). A separate SHA-256 implementation was tested on the standard `abc` vector and computed each raw GPX digest; **all four match the existing independent GPX manifests**. Byte lengths and actual XML trackpoint counts also exactly match.

| Operational night | Original SHA-256 (prefix) | Timed points | 2m+ stops | 5m+ stops | Stops close to logged captures | GPS jumps >130 km/h | Timestamp gaps >20s |
|---|---|---:|---:|---:|---:|---:|---:|
| Oct 6 | `f3f630b1` | 8,528 | 2 | 1 | 0 | 4 | 1 |
| Oct 8 | `c6c20c07` | 9,143 | 0 | 0 | 0 | 30 | 0 |
| Oct 14 | `b783411c` | 20,481 | 2 | 0 | 2 | 112 | 5 |
| Oct 15 | `4bc0d0e8` | 18,610 | 4 | 0 | 3 | 31 | 0 |
| **Total** | Four raw originals | **56,762** | **8** | **1** | **5** | **177** | **6** |

No groups passed the 10-minute (600-second) sensitivity threshold under these *specific* conditions. This does not mean there were no rest breaks: a stop involving GPS speed fluctuations, gradual repositioning or disjoint points may be missed.

The 8 detected stop groups total **about 29.03 minutes** of stationary-candidate time. Two October 6 candidates last 3m36s and 6m21s. The October 14 2m07s / 4m28s candidates both align with actual owner-capture records. Three October 15 stops (2m37s, 2m44s and 2m55s) align with owner captures. The remaining October 15 4m14s stop occurs after the nearby 22:25 capture but is **not within the strict 100m/10min stop-anchor association**; it remains UNKNOWN, potentially handling activity or rest. No blanket rest subtraction is defensible.

The October 8 Habu roadkill reaction remains an **occurrence reaction**, not a personally captured Habu. The six owner-capture events across Oct 14/15 remain six source records. The additional Oct 14 19:12 capture did not produce a 120-second stop under the heuristic and remains positive source evidence nonetheless.

## Next classification contract

- **SEARCH_MOTION_CANDIDATE:** GPX portions consistent with actual driving/exploration (owner reports habitual search), excluding known time gaps and unresolved stationary candidates. This is provisional exposure, **not certified Negative**.
- **EVENT_ASSOCIATED_STOP:** pause in/near a logged capture or reaction; preserve as search/capture handling candidate and **do not mark rest**.
- **UNKNOWN_STOP_PURPOSE:** sustained low-motion portion without sufficient event evidence; no assumed rest or Negative.
- **UNKNOWN_GPS_GAP_OR_JUMP:** gap, nonmonotonic timestamp or implausible adjacent-point jump; never interpolate continuous traversed roads.
- **REST_CONFIRMED:** **zero** intervals. Require independent context/owner session evidence before assignment.
- **NEGATIVE_CERTIFIED:** **zero** cells. The canonical `src/evidence_audit.py` contract still requires exact source roles, source-bound search session and capture logging receipts, GPS segment eligibility, reconciled owner-capture identities and absence of unresolved positives.

A 2-minute stop threshold is a model engineering candidate only. Review representative stop episodes (especially the two October 6 stops and October 15 22:29 onward) with original video/log/route context before selecting any production duration/geometry threshold. Apply multiple reasonable sensitivity settings on research nights and record the effect on inferred effort/Negative denominators; leave uncertain units Unknown.

**Scientific caution:** Consecutive GPS points are highly correlated. Neither 56,762 samples nor stop-candidate counts are independent Bernoulli trials, biological snake absences, official forecasts or evidence of improved P0 skill.

## Provenance and implementation gates

All source GPX and capture bytes remain unchanged. The accompanying JSON `2026-10-06_08_14_15-search-stop-candidates.json` records exact SHA-256, original Git blobs and every stop time/location/association, GPS gap/anomaly totals and scientific status. This is a **read-only derived audit candidate**, staged on existing PR #39 and requires independent reviewer/runner-backed exact-head CI before adoption in main or scientifically certified use.

The upstream full-source overlap (PR43 67 source capture events/68 individuals versus 11 already represented across main/PR39) remains identity-linked, never extra captures. Do not revise ORIGINAL P0 or Champion.
