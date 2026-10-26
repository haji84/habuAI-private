# August source family: closed 2026-08-23 three-statement batch v1

Status: **DESIGN_ONLY / DEPENDENCY_AND_INDEPENDENT_DESIGN_GATES_PENDING**.
Design base is actual verified main
`8c92f0fe912e3dc4266a255316329267ab60bc32`, on isolated branch
`codex/aug23-source-design-20261026`. This document is the only tracked change.
No Aug23 descriptor, CSV, final review, policy entry, qualification or executing
job is created by this design. The then-current main contains admitted Aug29 N1
and Aug24 N3. Reviewed Aug27 software at
`e0d25ea836246eb1fb0c56e36559f4676d232c8c` is a dependent reservation, not an
assertion that its software or canonical DATA has already passed future gates.

## 1. Purpose, choice and unresolved interpretation

Propose one closed batch of the three singular owner-capture SOURCE statements
L6199/L6209/L6672 from operational night **2026-08-23** and one actual shared
GPX. Reuse the existing `august-owner-capture-source-occurrence-v1` family and
the closed three-record shape. Append one literal admission; do not create a
per-night profile, matcher, parser, runtime candidate catalog or open registry.
Three separate descriptors would repeat the same trajectory work and complicate
global duplicate review. A 28-candidate bulk admission would exceed this scope.

The first pair is **120 seconds / 166.2557493559854 metres** apart. Distinct
native statements, differing behavior and disjoint source slices support review
as recorded occurrences, but do not establish different biological animals or
independently exclude repeated recording of the same event. Independent design
review must explicitly assess this disclosed **source-event duplication** issue
before implementation is dispatched. The existing frontier's joint
`<=1800 seconds AND <=100 metres` flag does not trigger; that absence is neither
a new dedup rule nor proof of uniqueness. Do not silently change that rule.

If independent review identifies an unresolved source-event duplicate in the
first pair, defer both and consider isolated L6672 as a separate N1 proposal.
That alternative requires an explicit revised selector/shape design and ROOT
dispatch; it is not automatic fallback or permission to silently drop records
from the N3 descriptor. No permanent biological-ID claim is proposed either way.
Aug19's close pair/plural issue, other unresolved quantities, 11 earlier aliases,
14 statements lacking paired original GPX and other-person/Himehabu/roadkill
records remain outside scope. Their existing originals are not called absent.

## 2. Native evidence and exact source selectors

The following are actual Git-native pins at the stated base. Native UTF8 bytes,
line endings, decimal strings and lossless selectors are preserved. Line ranges
are one-based inclusive; byte intervals are zero-based half-open and include the
actual trailing blank line. Slice hashes below are not normalized block hashes.

| Reference | Native bytes | SHA256 |
| --- | ---: | --- |
| `evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt` | 116496 | `130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c` |
| `evidence/recovered_sources/2026-08-native-original-library-byte-proof.json` | 1408 | `a62dd9d612766f6626e2561a0705dbb14cfd1d862e4afc84efec40da34494745` |
| `data/reconstructions/habu_captures/2026-08-count-correction-owner-confirmed-47.json` | 2551 | `4fe0fcd7c7e4f67f51d86fc6962d5c2b5ae78d9c04b86412356937f773158c92` |
| `data/raw/gpx/2026-08-23__legacy.gpx` | 6110544 | `ea3cbaca5cde18919e9b95fbabcbf66dbbd9c944f17e4c40da081c237c56def3` |

The TXT has 10506 logical lines, 10505 LF bytes, no final newline or CR/BOM.
The byte-proof establishes preserved
source-byte consistency, not independent device authentication or historical
forecast availability. Owner context remains August **47** and the dated
2026-10-20 cumulative **243**; it does not attest complete outcomes or permanent
identity. Preserve historical `log_byte_exact_native_original_verified=false`
and all other existing false/unknown fields rather than editing an old receipt.
Existing `dashboard/baseline_2026.json` (38548 bytes, SHA256
`29b25fa73bbe8f291caa314bd66239023c4292802aa70eb508f310775603e110`)
has Aug23 count3 and unknown search-wide times/coverage. This is aggregate context,
not an additional primary statement, complete ledger or identity certificate.

| Prospective source key | Native lines / coordinate lines | Native byte interval / length | Native slice SHA256 | Original local time |
| --- | --- | --- | --- | --- |
| `AUG2026SRC-L6199` | 6199–6208 / 6206,6207 | [70290,70412) / 122 | `abba28f65710b2ef71ca09ca0579d25dce234a560a5e151dc60ec51ae049433d` | `2026/08/24 0:02` |
| `AUG2026SRC-L6209` | 6209–6218 / 6216,6217 | [70412,70537) / 125 | `5070113502f30f10de9d0a6d7e2eb0dfb501f1205f96e0af6f4dbd6c9021c2dd` | `2026/08/24 0:04` |
| `AUG2026SRC-L6672` | 6672–6681 / 6679,6680 | [75123,75254) / 131 | `7b3427267d66381e66e8c87598525d3d7ae7bcda139fb879f93a5bca2fb43d55` | `2026/08/24 2:48` |

| Key suffix | Exact original latitude, longitude | Native event/note; behavior; microhabitat; surface; place |
| --- | --- | --- |
| L6199 | `28.19081506904525`, `129.3980626956513` | 捕獲 / ハブ捕獲小; 伸び; 道路脇; ドライ; 瀬戸内町嘉徳 |
| L6209 | `28.19212476906661`, `129.3972355960724` | 捕獲 / ハブ捕獲小; とぐろ; 道路脇; ドライ; 瀬戸内町嘉徳 |
| L6672 | `28.17491855810635`, `129.3047488375334` | 捕獲 / ハブ捕獲小; とぐろ; 道路脇; ウエット; 瀬戸内町久根津 |

Each record is a singular capture statement, not literal `1匹`. The proposed
integer count1 means `SINGULAR_STATEMENT_AS_ONE_RECORDED_OCCURRENCE`; `小` is a
source size category, not a measured length, and sex stays empty/unknown.
JST times are respectively `2026-08-24T00:02:00+09:00`,
`2026-08-24T00:04:00+09:00`, `2026-08-24T02:48:00+09:00`.
All belong to operational Aug23 under the unchanged 07:00 Asia/Tokyo boundary.
There are no newly assigned data IDs here: the displayed keys are prospective
derived SOURCE-occurrence keys, never permanent animals or changes to old IDs.

The first two intervals touch at70412, without overlap. The isolated third is
9960s/9327.205061928726m from L6199 and 9840s/9276.160351403096m from L6209.
All three are disjoint under the same primary SHA from these reserved intervals:

| Existing/dependent cohort | Reserved half-open bytes |
| --- | --- |
| Aug29 L9654 | [107486,107604) |
| Aug24 L6791/L7201/L7351 | [76701,76818), [80948,81074), [82547,82653) |
| Dependent Aug27 L7853/L8052/L8214 | [87936,88061), [90248,90358), [91934,92056) |
| Protected Aug31 L10110/L10492 | [112368,112489), [116249,116392) |

Sept28 uses its separately protected primary source. Future global preflight
must use ALL actually admitted descriptors and protected legacy selectors/IDs,
not merely this table. Aug27's reserved IDs/spans cannot be reused while its
registration is pending. No source alias in the frontier was attached to these
three statements; that is not a universal animal-dedup proof.

## 3. Real GPX, raw chronology and unchanged match contract

Catalog name is `2026-08-23-探索.gpx`. The incoming same-SHA copy
`incoming/gpx/ea3cbaca5cde18919e9b95fbabcbf66dbbd9c944f17e4c40da081c237c56def3__2026-08-23__legacy.gpx`
was byte-compared equal: one transport alias, not an additional track/capture.
No new Raw, replacement trajectory or receipt normalization is proposed.

Actual bounded feasibility ran genuine old Core14740 bytes/SHA256
`297b2bb4301a0234b61e63abaf92076390095957be054bce008e7d49c5b1a914`
and reviewed Aug27 Core16292 bytes/SHA256
`9272a708b794756bb5919d6aadfff2c0658a8534f42a8414c6f9fd0f6240b8dc`
on this track, both with the empty/strict default. Each charged23086 points and
458419 ticks; whole canonical points+QC SHA256 was identically
`f79aebd6254f4f905988bd399aa62a4f591b9521af0a0beb759fe5faee4107f4`.
Observed raw23085 intervals: minimum0.233s, maximum17.216s, **zero0/negative0**.
Frozen marker QC:23086 points, excluded0, segment_breaks0, maxgap17.216s;
all raw points belong to operational Aug23. The unchanged parser/matcher source
`gpx_audit.py` is12860 bytes/SHA256
`878ff42ec767e671bf9581ce2d1635c5282ffca469dc6f247654817b7c55779d`.

| Source | Actual point index / XML sequence | Actual UTC point | Unrounded distance / absolute time residual | HDOP / immediate gaps |
| --- | --- | --- | --- | --- |
| L6199 | 10427 / 93059 | `2026-08-23T15:02:02.999000+00:00` | 0.006734735183475305m / 2.999s | 4.687 / [1.0,1.0]s |
| L6209 | 10530 / 93979 | `2026-08-23T15:03:45.999000+00:00` | 2.82418096119049m / 14.001s | 4.687 / [1.0,1.0]s |
| L6672 | 20382 / 181990 | `2026-08-23T17:48:13.999000+00:00` | 0.00270291971135229m / 13.999s | 4.687 / [1.0,1.0]s |

Each selected point is real, unexcluded and not a break start, with two positive
immediate gaps<=30s and HDOP<=10. Preserve existing100m/600s tolerance, tie/order,
Decimal source-coordinate conversion, marker, selected-neighbor checks, and
existing Core serialization/rounding (descriptor distances0.007,2.824,0.003m).
Keep unrounded inspection facts separate from rounded proof fields. No inverse
projection, interpolation, added exclusion, timestamp repair, route bridge or
inferred search effort. Parse this shared GPX once per ordinary reproduction,
charging every point; do not parse per record or exempt rejected/rescan work.

These genuine strict controls show no observed chronology/QC gap for this track;
they are **not** full new-profile acceptance or a claim that implementation tests
have run. Aug23 must use `allowed_equal_time_edges=()` on the then-reviewed Core.
The closed Aug27 edge/path/night/SHA rule may never apply here. Any new observed
Core incompatibility blocks implementation pending a separate reviewed scope;
this design does not authorize Core changes.

## 4. Proposed later literal admission, unchanged schema and interfaces

Only after prerequisites and explicit runtime dispatch, create exactly these
three software artifacts, initially diagnostic and without final registration:

- `evidence/source_reviews/august-2026/admissions/2026-08-23-batch-v1.json`
- `data/processed/capture_events/source_reviews/august-2026/2026-08-23-batch-v1.csv`
- `data/processed/individuals/source_reviews/august-2026/2026-08-23-batch-v1.csv`

Append their actual independently checked size/SHA/pins to `ADMITTED`, with the
literal shape `('2026-08-23',3)`; retain all old tuple order/bytes/pins. The new
descriptor uses unchanged schema `habu-august-source-occurrence-descriptor-v1`
and family `august-owner-capture-source-occurrence-v1`. No caller-selected size,
unlimited selectors, arbitrary source/ref, new profile or candidate-catalog input.
New derived file byte hashes must be measured during implementation; this design
does not supply placeholder/guessed hashes or create those files.

Exact descriptor keys remain schema_version,family_id,primary_ref,
native_byte_proof_ref,owner_context_ref,gpx_ref,records,captures_ref,occurrences_ref,
expected_counts,expected_gpx_qc. Ordinary refs have exactly path,size_bytes,sha256;
gpx_ref also has point_count=23086. All sizes/counts/indices are exact integers,
not bool/float equivalents. JSON duplicate keys at every depth, nonfinite values,
extra/missing fields and malformed hashes/types fail. Shared128KiB/structural
limits remain unchanged. Exact counts are `{events:3,source_occurrences:3}`.

Records in ascending source order6199,6209,6672 retain the exact20 keys:
behavior,coordinate_lines,count,count_basis,event_id,event_place,legacy_aliases,
microhabitat,operational_night,primary_sha256,sex,size_note,source_byte_end_exclusive,
source_byte_start,source_line_end,source_line_start,source_note,source_slice_sha256,
source_time_jst,surface. Every record binds its own exact values above, empty
legacy_aliases/sex and count1; no first-row validation borrowed for later rows.
CSV headers, order and types stay unchanged. Capture rows use the three source
keys, capture/count1, exact original decimals/times/attributes; occurrence rows
use each source key plus `-OCC01`, index1, and the matching record's attributes.
This preserves occurrence accounting, not permanent biological identity. Joins
must be exact1:1 with no missing, reordered, duplicate or invented individuals.

expected_gpx_qc is exactly `{track,selected_points}`; track has exact four keys
point_count=23086,excluded_points=0,segment_breaks=0,maximum_gap_seconds=17.216.
All three selected rows, in record order, have the exact existing eight keys:
event_id,gpx_sequence,gpx_trackpoint_index,gpx_time_utc,distance_m,
time_delta_seconds,hdop,neighboring_gap_seconds. Each value is bound to its own
row, actual point and unchanged rounding. Reject poisoned last rows even if the
first two match. All existing pure APIs/signatures/proof fieldsets remain:
`reproduce_sources(descriptor_ref,*,read_ref,tick,consume_point)`,
`verify_review(review,*,read_ref,tick,consume_point,now)`,
`preflight_declarations(policy_raw,*,read_ref,tick,consume_point,now)`.

## 5. Global staging, ownership, safety and resources

Reuse family-only global ALL ADMITTED preflight before any family outcome role
is published. Duplicate/overlapping `(primary_sha256,byte_start,byte_end)` across
all batches/transports, reused IDs, duplicate declarations and portable aliases
fail atomically. Nonoverlap alone does not resolve the first pair's source-event
interpretation; independent review in section1 remains necessary. Preserve exact
canonical capture/occurrence/descriptor/review paths and conservative family
intent recognition, including known review refs. Case/separator/dotspace/DOS/ADS/
drive/C0/DEL aliases participate in rejection, never normalization for opening.
Malformed path/ref types fail locally before reads, with no canonical family
role retained. Keep genuinely nonfamily Sept28/Aug31 behavior unchanged.

All public paths keep independently owned input snapshots, saved lineage and
outbound ref copies for first/final reads. A legitimate reader may verify bytes
then mutate its borrowed ref without corrupting retained lineage. `read_ref`
must itself verify guarded path, actual size and bytes/SHA; ownership does not
authenticate arbitrary callbacks or issuer claims. Production uses actual
`Audit.ref`, including first-open and final-rescan reparse/path guards. No new
namespace, permission, cache exemption or generic filesystem confinement claim.

Use the same caller's absolute remaining deadline, actual-byte/read ledger and
point counter through parse/hash/matching/all-registry preflight/rescans/seal.
Retain ordinary callback exception object identity, including OverflowError,
KeyboardInterrupt, cancellation and resource classes; narrow pure bad-time
ValueError handling cannot swallow callbacks. Charge rejected work and actual
lengths. Apply size/depth/copy bounds before allocation and fully sealed output
bounds/checks before return, without changing existing limits or Core behavior.
One context remains **512MiB / 300s / 4000 reads / 1M point charges** for the full
public audit. No deadline reset, pooling prep+verify contexts or cap raise.
Cooperative checks do not claim hard preemption of parser/native syscalls.

There is no measured new-profile full-audit cost yet. Track23086 is below the
existing point ceiling individually, not proof of the combined audit fitting.
Implementation must measure default/private complete-input audits under the
unchanged caps; failure means blocked, not a rationale to exempt work or raise
limits. UNKNOWN comparisons use identical requested Aug23 night/unit keys only,
never Aug24/Aug27/Aug29 totals as interchangeable denominators.

## 6. Prerequisites, old oracles and implementation ownership

Runtime authorization is explicitly pending: (1) actual Aug27 SOFTWARE #132
exact-head and fresh-main success, (2) separately dispatched actual-current-time
Aug27 canonical DATA review/policy registration and its own exact/fresh success,
(3) independent Aug23 design/source-duplication review and ROOT acceptance,
(4) explicit ROOT implementation dispatch on the then-verified base. No future
heads, registration timestamp, PR number or completed CI is invented here.

Before any later code/test/data edit, normally merge only ROOT-specified verified
main, seal a complete NUL-safe native `ls-tree`/raw `cat-file` inventory and
genuine pre-extension old-program capsules, then capture registered N1/Aug24/
Aug27 direct reproduce+verify FULL typed proofs, canonical/self hashes, all refs,
point/read/open/interleaving/tick ledgers at the SAME recorded actual fixed now
using their actual canonical final reviews. Aug27 registration must really exist
first. Preserve old Aug31/Sept whole controls, including historical362-catalog
receipt plus independently complete387/25-omission catalog proof; no golden or
capsule regeneration from new code. Freeze source/dependencies and compare exact
whole objects/ledgers in identical contexts. If an additional old-source capsule
is needed in CI, request its exact path/pin from ROOT before touching it.

Appending a descriptor necessarily expands global metadata discovery/reads and
public input closure. Preserve old direct per-admission proof/verify behavior;
measure new expanded public closure separately rather than force old public
whole hashes or delete global checks. Explicit actual available_at clock changes
and qualified-row relative order must be enumerated, not hidden as exact bytes.

Proposed later software ownership is limited to:

- `src/august_positive_source_review.py`: one append-only literal pin/shape only.
- The three new software data files in section4.
- `tests/test_august_source_batch_20260823.py` (new); fixture-only additions to
  existing family tests only if specifically dispatched, without changing old assertions.
- This spec's status/evidence and new author record
  `docs/reviews/august_source_batch_20260823_20261026.md`.

Core, evidence auditor, marker, matcher, legacy facades, Raw/incoming, old reviews,
capsules/goldens, policy, models/registry, parent, requirements/workflows,
STATE/current-cycle/freeze/permissions remain outside scope. Stop and report an
actual incompatibility before broadening these paths. No final Aug23 review is
created or committed in the software slice. A later independent ROOT registration
dispatch alone may create the new review at
`evidence/source_reviews/august-2026/2026-08-23-batch-v1.json` and append its sole
capture-CSV policy entry at actual current time after software exact/fresh gates.
No prereveal time/backdating or old review overwrite; old policy semantics,
sessions and outcome_coverage remain exact. Registration has its own independent
data acceptance and exact/fresh gates, not inherited software CI credit.

## 7. Required future TDD and actual acceptance (not executed by this spec)

1. Capture the old baselines first; independently resolve the section1 source-
   event interpretation. Run missing-admission tests RED before appending pins.
2. Prove literal N3 crosswalk/QC/three rows/one GPX parse GREEN. Bind exact raw
   slice hashes and all20+8 fields; no placeholders or quantity generalization.
3. Poison each record and selected row at every position: time/night/coordinates/
   quantity/bool/type/source SHA/IDs/selectors/QC/neighbor/endpoints/exclusion/
   breaks/extra/missing fields/duplicate JSON. Validate all known contradictions,
   not a partial first-row proof. Default strict zero/negative control must fail;
   attempting to borrow Aug27's edge opt-in for this track must fail.
4. Test ALL ADMITTED duplicates/overlaps/aliases and invalid entries first/middle/
   last, both old/new declaration orders, missing/unknown review profiles and
   downgrade attempts. Invalid last work publishes no family qualification;
   legacy profiles retain their appropriate unchanged roles.
5. Run three public seams with ref-loan mutation and same-object exceptions at
   first/middle/final callbacks, hash/seal expiry, size/growth/budget exhaustion,
   late review/descriptor/source mutation. No successful partial proof/role.
6. Use genuine Windows junction/POSIX symlink fixtures and guarded actual reads
   to verify zero forbidden payload opens, accurate platform skips and safe
   link-only cleanup. No fake OS/fcntl or mocked proof of confinement.
7. Compare all old direct whole artifacts/read/open/ref/tick results and unchanged
   Sept28/Aug31 controls at fixed contexts. Run affected real family/source tests,
   native file/hash checks and diff checks; retain all failures and corrections.
8. Seal exact software source; run ONE default complete-native public source audit
   and ONE separate private provisional Aug23 review/policy audit at actual clocks,
   unchanged caps and all tracked native inputs before/after. Preparation/verify
   contexts are separate and never pooled. Enumerate the only private review+
   sole-policy delta, all physical/full result/self hashes, counters, qualified
   event/SOURCE-occurrence/positive definitions, old-row clock deltas, same-night
   UNKNOWN transitions and old/all-native immutability. Default registered
   qualifications must not change; private additions are measured, not assumed
   and never declared registered. No redundant older a6/f422/685 audit replay.
9. Independent exact-source/data review plus actual Ubuntu exact-head/fresh-main
   software gates are required before a separate final-registration dispatch.
   A CI or source-consistency PASS never becomes scientific/accuracy PASS.

## 8. Authority, risk and private evidence provenance

Risk: **MEDIUM bounded closed source-consistency design**, conditional on explicit
source-event duplication review and no Core/default changes. HIGH changes to Raw,
historical identity/dedup/scientific target rules, search/complete-outcome scope,
training or production permissions are not included. All eight review authority
flags remain literal false: negative_eligibility_assigned, search_scope_certified,
complete_outcome_coverage_claimed, training_authorized, confirmation_authorized,
official_issuance_authorized, promotion_authorized, production_authorized.
Device authentication and permanent biological identity stay NOT_ESTABLISHED;
cohort exposure RESEARCH_EXPOSED. Source-positive consistency does not create
Negative, complete denominator, historical ex-ante features, TRAIN, real fit,
formal performance, confirmation, model selection, official P0 or production
authority. No actual learner/parent/425 replay is part of this design or acceptance.

Private inspected packet (outside Git), observed2026-10-26T03:45:12.375147Z:
`august-next-source-feasibility-after-Aug27-20261026/packet.md`,6726 bytes/SHA256
`68619b03929e416068fb6803764cdd3b31edfdc9ec23adef64a79eede263b77d`;
`packet.json`,11688 bytes/SHA256
`f49ffec8e80f85ae499b5d0a4319c55588e13648916aa9555502d45456317989`.
It reuses immutable frontier90229 bytes/SHA256
`8a00593c27e57f5fdf954a29b18ac38f7558e392ad1d2f0dc570d91feca7d8c6`
and records exact native transcripts, coordinates, pairing, dependencies and
reserved selectors. The prior feasibility inspection actually used22 Git-native
payload reads/24843936B, two genuine strict parser controls on12221088B already-
read input,46172 point charges/916891 ticks,3.7660000000032596s. Those are bounded
private-analysis counters (including rereads), not an actual `Audit` or model run;
dependency-import I/O is not misreported as source-payload I/O. No reparse of all46,
full public audit, source qualification, code/data/index change or registration
was performed. This design adds no new runtime evidence claim or user-upload
request. Current source originals are present; their qualification boundaries
remain explicit.
