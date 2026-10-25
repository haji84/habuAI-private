# Independent M1/M2 candidate and current-cycle cursor review

Lane V reviewed sources in separate M1/M2/integration worktrees. This reviewer
did not edit their fitting code, helper, cursor, tests, shared STATE or original
data. Every executed fit below uses explicit synthetic unit-test fixtures,
never actual Habu observations or newly revealed confirmation outcomes.

## Scope and disposition

M1: research-only Beta-binomial 1km empirical shrinkage of qualified binary
owner-capture observation units. M2: fixed-strength hierarchical spatial/clock
shrinkage diagnostics. Shared helper consumes the existing PR46 selector return
shape and PR32 label-free full joined forecast rows. Independent confirmation,
calibration, formal targets/KPIs, routes and production authority remain blocked.

**CODE REVIEW PASS for the bounded research implementations and read-only
cursor**, after owner repairs and independent reruns at the exact identities
below. No unresolved implementation defect was found in this reviewed scope.
Exact-head Linux CI and fresh-main verification remain integration gates;
scientific and production qualification are not granted.

## Defects found and repair verification

1. M2 originally accepted rehashed serialized models with an unregistered family,
   held-out-night fit cutoff after 07:00, zero training nights, invalid corpus
   hash, or an extra `official_issuance_authorized=true` field. Independently
   reproduced all five on source SHA
   `bf61ac94d25963fa2bfd9ad3b44e2d2662886c85e4ceac8e1deee35a2edfdbcb`.
   The implementation owner added exact root fields, fixed family/qualification,
   lineage/schema, count types/class minima and time checks. On source
   `f22b25ddc4a8e8cec0837dd1654c5a817035fe3154313639f88a24b8c2ac8bcf`,
   all five independent probes now reject. Independently executed M2's 16 tests:
   PASS, 4.862s.
2. The shared forecast helper rejected projected easting 10,000,000m but accepted
   the same location supplied only as `cell_x=100000`. The owner fixed the
   cell-only forecast branch to the same physical UTM easting extent in commit
   `2faf5f81102d3e17c06bfd72dc793d4636aef1a8`. Training's existing PR46 cell
   range remains separate for compatibility. Shared helper 25 tests independently
   PASS, 0.042s. M2 changed its large synthetic capacity fixtures to physical
   two-dimensional cells instead of out-of-domain eastings.
3. M2 then accepted a rehashed fit cutoff in 1900 because serialized training
   nights were absent. M1 `327fe127b1b6789d44e260e9eb02a008969db554` correctly
   rejected that case and held-out-night cutoffs, but still accepted
   `2026-09-03T07:01+09:00` while its fixture's latest training window was
   September 3 at 20:00. Both need actual accepted training-night/window metadata
   to reject a fit cutoff before the model's own declared training observations.
   Both owners added actual accepted maximum-window metadata. M2 additionally
   retained its sorted unique actual training nights. Independent final probes
   now reject a cutoff in 1900, before the latest actual training window, and
   equal to that window, for both models. Window metadata must be aware, aligned
   and consistent with the model's latest training night. All original five M2
   malformed-model probes also remain rejected.

The global source-receipt list also includes rejected/unused source artifacts.
Requiring every global receipt to precede fit would incorrectly reject valid
accepted rows. The helper now retains these metadata without claiming it can
reconstruct discarded accepted-row source references or audit/label readiness.
Upstream repaired selector validation remains mandatory; consistent hashes are
not evidence authenticity.

## Actual API interoperability, synthetic evidence only

Independently invoked the **actual repaired PR46 `select_training_rows`** in the
feature worktree using its test fixture with separate active-search and complete
outcome receipts. Its actual output had four accepted rows, three prior nights,
two positive units and two negative units; the shared helper accepted that exact
unmodified return envelope.

Then invoked the **actual PR32 `load_prospective_inputs`** against a temporary
hash-bound synthetic forecast universe and feature snapshot. The registered
feature name was aligned with the selector (`road_length_m`). Its two actual
joined future rows, including their exact coordinates, source bindings and
availability, were passed directly to M1 and M2. Both returned both rows. M1
reported `DEVELOPMENT_FIT_ONLY`; M2 reported `DEVELOPMENT_CANDIDATE_FITTED`; both
retained `NOT_VALIDATED`. This proves interface mechanics on fixtures, not any
real-data fit, ex-ante historical availability or measured prediction skill.

Repeated this direct interoperability check after the final temporal fixes:
both final models retained `training_window_start_max=2026-09-12T21:30:00+09:00`,
scored both future rows and returned NOT_VALIDATED/production false. Actual API
source working bytes used by the independent fixture execution:
`training_corpus.py` SHA-256
`f14e56a948ddb0d42201182386a49dda803bf1ff05fef264ffe03c5a3863edd5`;
`prospective_inputs.py` SHA-256
`52981dcab79a696f8f38907b03fef3fe4301904a7e699b8268dbca0402200775`.

## Algebra, geometry and scientific boundaries

Independently checked the fixed formulas against hand-derived small examples:
global `(k+1)/(n+2)`; M1 area `(k_area+4*p_global)/(n_area+4)` gives 4/7 and 3/7
for the balanced fixture. M2's positive branch through 1km/500m/250m/100m/clock
gives `1/2, 1/2, 5/7, 41/49, 311/343`. Child sufficient statistics must partition
parent counts, while unseen nodes inherit their nearest parent's score.

M2 uses a **100m cell origin proxy**, since PR46 accepted rows retain integer
cells rather than original points. At 250m boundaries that is not true original
point membership. Both model and prediction explicitly carry
`CELL_ORIGIN_PROXY_NOT_POINT_GEOMETRY`; no formal spatial/time target or correct
point-level 250m result is claimed. Clock bins are repeating JST categories,
explicitly without adjacent-slot smoothing. M1's 1km grid is aligned with the
retained 100m cells and its probability semantics remain conditional on qualified
observation units, not biological island occupancy.

Malformed/UNKNOWN/boolean labels, duplicate units/events, changed selection
hashes, outcome-bearing future rows, missing/nonfinite predictors, cutoff
equality and inconsistent coordinates are rejected. Joined-row digests bind all
supplied forecast rows, including unseen units; they do not prove the caller
supplied an authentic complete universe or a complete out-of-universe outcome
denominator. Rehashed model data must still satisfy fixed recipe and internal
statistical/time/authority constraints.

## Current-cycle cursor independent review

Reviewed integration `scripts/check_codex_cycle.py`, working-byte SHA
`4d74878ba44a916a5042e9aad3ecf6e28fb25878e7af9a36c3d3b132a453b159`, and
`tests/test_codex_cycle_cursor.py`, SHA
`165770e8fdd25e9df9a99fd3dfb3c975058a869d2b879bd5a644087269e904d7`.
Exact reviewed cursor commit:
`6fcb6ce031c563b1d08b92707b4a99e613a893df`. Its committed source differs only
by checkout line endings, independently compared after CRLF/LF normalization;
the test bytes match exactly. The committed source SHA-256 is
`5592ab24503b79f1df3fef529e280fb872972b556a26b34b13de47a68b95f85a`.

Independent cursor 6 tests PASS (0.157s) plus G0 19 PASS (0.283s). Additional
independent probes confirm valid legacy fallback and rejection with
`CURSOR_CHANGED` if a cursor appears while fallback validation is running.
The read-only cursor binds exact target bytes under the cycle namespace,
rejects traversal/unsafe paths, unknown/duplicate keys and invalid hashes, and
rechecks manifest/pointer bytes after the same `validate_cycle` call. It leaves
the historical frozen G0 bytes untouched. It inherits unchanged false fit and
production authority and NOT_VALIDATED science. Sequential rechecks do not claim
an atomic snapshot or a trusted pre-reveal timestamp.

## Final exact identities and verification

| Component | Final reviewed Git commit | Independently executed targeted tests |
| --- | --- | --- |
| M1 | `40ddf218a34dd32f1fb818e11fdec8a6a5b78095` (body `327fe127b1b6789d44e260e9eb02a008969db554` plus temporal repair) | 16 PASS, 0.069s |
| M2 | `1f3d34bfebe51e5de384ee3ac0dcc94e2c6a1c29` | 18 PASS, 9.668s |
| Shared selector/future gate | M1 `2faf5f81102d3e17c06bfd72dc793d4636aef1a8`, identical committed helper on M2 | 25 PASS, 0.042s |
| Current-cycle cursor | `6fcb6ce031c563b1d08b92707b4a99e613a893df` | 6 cursor + 19 original G0 PASS |

Final committed source SHA-256:

| Path | SHA-256 |
| --- | --- |
| `src/models/research_selection.py` (both branches) | `915fbe3bb52cbf211c3ed7974ac805c0bb87e70bc0378837544b0081d27dd714` |
| `src/models/occupancy_shrinkage.py` | `48443068e2aeaacf7f9a638a604fe72d063aa3891bc1652f713f9e60c7e34c2a` |
| `tests/test_occupancy_shrinkage.py` | `d6bfb7941fa9c063e9a0421a0b12c9651a7426a2294607529ff74a1abb59d584` |
| `src/models/hierarchy_shrinkage.py` | `85cb9beddc6128522a35e45f7695976781bd01632adce4e6415a429450131b71` |
| `tests/test_hierarchy_shrinkage.py` | `f731402a6fcbab2a690002a2903b48c310e5cf72ba753b6ecab7baf999072107` |

All three final commit diffs pass `git diff --check`. M2's working helper copy
has CRLF while M1's has LF; their committed helper bytes are identical.
Existing model owners' Windows full-suite logs remain environment/source
blocked (M1 368 tests, M2 370 tests; each one failure and 105 errors), with all
nonpassing identities retained in their implementation reports. This review
does not label those runs green or substitute fixtures for exact-head Linux CI.

## Final checkpoint consistency review

The independent V reviewer read the final uncommitted checkpoint without writes,
verified all63 source references against Git index bytes, the pointer SHA and the
exact-source snapshot CLI `CONTRACT_VALIDATED` result. Scientific fit0/0,75UNKNOWN,
unallocated folds, parent PDCA not connected, remaining implementation work,
Windows full-suite non-PASS and unattended executor false were consistent.
M2 push-main and PR50 CI were pending at this review. Result: CHECKPOINT_REVIEW_PASS.
