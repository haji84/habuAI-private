# August source family: closed 2026-08-24 three-record batch v1

Status: **DESIGN_ONLY / DEPENDENCY_PENDING_SOFTWARE_AND_REGISTRATION**.
Design base: actual main021de78514871a6e2aa0c3cc7070d78e93a4e21c (891 files).
Branch:codex/august-source-batch-20260824-20261026. This base does NOT contain
src/august_positive_source_review.py or src/_owner_capture_occurrence_core.py.
The initial family is a pending dependency, referenced read-only at source
48d06f628f0981bf256f19dffe8c988b5e8cff26 / author d60f669c7b13736c707151b5bac7a0b55acda493;
its exact software/fresh-main and separate Aug29 registration gates must finish.
This document creates no implementation, descriptor, CSV, review, policy entry,
source qualification, running job or model fit. Root AND independent V design
approval, followed by explicit implementation dispatch, are still required.

## 1. Scope and choice

Reuse the initial closed August family and its shared occurrence core for ONE
new append-only descriptor containing the three singular capture statements
L6791/L7201/L7351 from one original GPX/operational night2026-08-24. Do not add a
per-night profile, copy its matcher, introduce a generic upload/registry layer,
or require the private28-candidate frontier at runtime. The alternative of
three descriptors would repeat track reads/parses and make duplicate admission
harder; treating all28 as approved would exceed this reviewed source scope.

This is a MEDIUM bounded source-consistency extension. HIGH changes to canonical
originals/old IDs/receipts, search or complete-outcome criteria, permanent animal
identity, Negative/TRAIN/scientific labels, permissions, model registry or
production authority are NOT authorized. New stable keys below are prospective
derived source-occurrence keys, not permanent biological IDs or edits to old data.
Owner47/243 and historical false/unknown fields remain unchanged. The initial
frontier's other candidates,11 role-alias cases, ambiguous Aug19/plural cases,
14 missing-original-GPX capture statements, other-person/Himehabu/roadkill etc.
are outside this batch; their source originals are not declared absent wholesale.

Evidence basis: private next-admission audit11246B/SHA
669267e239e59b4e253d0dd4cd0cb4d6d33d40c8e3a90f04b0f49708f4f29569 and compact
receipt8542B/SHA7a995f7f824d993b88787edb834eded496ede569dc7d16864e8e57c894f5e5df,
both named august-family-next-admission-batch-audit-20261026 under .worktrees.
The immutable frontier90229B/SHA8a00593c27e57f5fdf954a29b18ac38f7558e392ad1d2f0dc570d91feca7d8c6
is private feasibility evidence, not a runtime input or28 approvals. Its source
pins were reread at d60f669; all four primary/source GPX Git blobs also equal the
actual021de base. No network, upload or new primary evidence is required here.

## 2. Frozen native evidence, selectors and count interpretation

The same three primary references as initial Aug29 remain exact:

| Reference path | Bytes | Native SHA256 |
| --- | ---: | --- |
| evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt |116496|130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c|
| evidence/recovered_sources/2026-08-native-original-library-byte-proof.json |1408|a62dd9d612766f6626e2561a0705dbb14cfd1d862e4afc84efec40da34494745|
| data/reconstructions/habu_captures/2026-08-count-correction-owner-confirmed-47.json |2551|4fe0fcd7c7e4f67f51d86fc6962d5c2b5ae78d9c04b86412356937f773158c92|

One original GPX:data/raw/gpx/2026-08-24__legacy.gpx,5645516 bytes,
SHA5995bc3e8addb65f873d1416f57f18153b9a5d769bf48ff4ffb84f3c581bc671.
Its incoming/gpx copy sharing that raw SHA is a transport alias, not another
capture or track. The full native-source byte proof establishes preserved byte
consistency, not independent device cryptography or historical ex-ante availability.

Line spans are one-based inclusive; byte intervals are zero-based half-open and
include the actual source trailing blank line. These SHA values hash EXACT native
UTF8 slices, never normalized extracted blocks:

| Prospective source key | Lines | Native bytes / SHA256 | Original local time |
| --- | --- | --- | --- |
| AUG2026SRC-L6791 |6791–6800|[76701,76818),117B /2c99420caa10cd6d82199747daebad27d6ffcc91a7ee2823f482ec60ef6535bc|2026-08-24T21:10:00+09:00|
| AUG2026SRC-L7201 |7201–7210|[80948,81074),126B /be156b075377f98a1f562083def11ad6bc07a933367ebdf02dd03d7da8bf525b|2026-08-24T23:58:00+09:00|
| AUG2026SRC-L7351 |7351–7360|[82547,82653),106B /47c5c65b2f11b17371f8717ce79e0a6bbf4bfba7e3e8258fcacf2b47305a903b|2026-08-25T00:51:00+09:00|

| Key suffix | Exact coordinate lines / decimal strings | Source note; behavior; microhabitat; surface; place | Size note / sex |
| --- | --- | --- | --- |
| L6791 |6798/6799:28.18546459772124,129.3077046392419|ハブ捕獲大;移動中;道路脇谷側;ウエット;empty|大 /empty|
| L7201 |7208/7209:28.16462460150211,129.3950149001608|ハブ捕獲中;伸び;道路中央;ドライ;瀬戸内町節子|中 /empty|
| L7351 |7358/7359:28.1690951721759,129.3960943922356|ハブ捕獲大;移動中;道路脇;ドライ;empty|大 /empty|

All have the exact preceding event line 捕獲. Each is1 recorded occurrence under
SINGULAR_STATEMENT_AS_ONE_RECORDED_OCCURRENCE, not a literal1匹 claim. Existing
day-count3 is context, not newly authenticated complete outcomes. 大/中 are size
categories, not measured lengths; missing place/sex remain empty/unknown.
The third calendar-date record belongs to operational Aug24 under07:00JST.
No evidence here establishes three distinct physical animals or search/Negative scope.

All three slices are mutually disjoint and disjoint, under the same primary SHA,
from L9654[107486,107604),Aug31 L10110[112368,112489),L10492[116249,116392).
Pairwise source separation is10080s/8876.266m,13260s/8864.042m,3180s/506.461m;
none triggers the frontier's <=1800s/<=100m near-pair concern. Frontier legacy
workbook aliases are empty for these three; this is not universal animal dedup proof.

## 3. Exact three-record descriptor and derived artifacts

Prospective paths ONLY; none is created by this design:
- evidence/source_reviews/august-2026/admissions/2026-08-24-batch-v1.json
- data/processed/capture_events/source_reviews/august-2026/2026-08-24-batch-v1.csv
- data/processed/individuals/source_reviews/august-2026/2026-08-24-batch-v1.csv
- evidence/source_reviews/august-2026/2026-08-24-batch-v1.json (final review, separate registration stage)

Reuse descriptor schema habu-august-source-occurrence-descriptor-v1 and family_id
august-owner-capture-source-occurrence-v1. Exact top-level fields stay:
schema_version,family_id,primary_ref,native_byte_proof_ref,owner_context_ref,gpx_ref,
records,captures_ref,occurrences_ref,expected_counts,expected_gpx_qc. Ordinary refs
are exact {path,size_bytes,sha256}; gpx_ref adds point_count. Reject extra/missing
fields, bool-as-int, nonfinite values, malformed hash/size and unadmitted paths.
New descriptor and both CSVs receive independently checked exact native size/SHA
pins during approved implementation; no guessed/zero placeholder pin is accepted.
Pin exact reviewed N=3 per this new admission, not arbitrary caller quantity or a
range expansion. Existing initial N=1 descriptor2424B/SHA
0582d7b6150d6dcc9cbffcd568172fdb23feab5d4b47ba3f32e0331eb693f32c is unchanged.

records has exactly three rows, in ascending source order6791,7201,7351. Every row
has the dependency's exact20-field record schema:behavior,coordinate_lines,count,
count_basis,event_id,event_place,legacy_aliases,microhabitat,operational_night,
primary_sha256,sex,size_note,source_byte_end_exclusive,source_byte_start,source_line_end,
source_line_start,source_note,source_slice_sha256,source_time_jst,surface. Validate
ALL rows before constructing the shared Definition:exact native facts above,
literal integer count1,empty legacy_aliases,same pinned primary SHA and operational
night,valid selectors,distinct IDs. Do not borrow first-row validity/night/quantity
for later rows. expected_counts is exactly {events:3,source_occurrences:3} with
integer types. N=1 remains the exact closed old admission; there is no plural support.

Capture CSV has exactly3 rows with unchanged ordered header:
event_id,operational_date,event_time_local,event_place,event_type,event_count,latitude,
longitude,surface,source_note. Each event_type=capture,event_count=1,original decimal
strings and all attributes above bind1:1 to the native record. Occurrence CSV has
exactly3 rows/header:individual_id,event_id,individual_index,operational_date,
event_time_local,event_place,size_note,sex,behavior,microhabitat. Each prospective
ID is the source key plus -OCC01,individual_index=1; all fields bind the same row.
These are source occurrences, never permanent animal IDs. Unique/complete3-row
joins and exact order are required; dropping/reordering/duplicating a row fails.
The actual UTF8/LF bytes, sizes and SHA are frozen before admission review, not
normalizations of old Raw or an automatic qualification by a new derived file.

QC is exact:{point_count:21246,excluded_points:0,segment_breaks:1,maximum_gap_seconds:32.58}.
selected_points is exactly3 rows in records order. Each has the same exact8 keys:
event_id,gpx_sequence,gpx_trackpoint_index,gpx_time_utc,distance_m,time_delta_seconds,
hdop,neighboring_gap_seconds. Require every row's fixed fieldset/types and binding;
using only selected_points[0]'s keys is not sufficient for this extension.

| Key suffix | Point index / XML sequence | Actual point UTC | Core-rounded m / s | HDOP / immediate gaps |
| --- | --- | --- | --- | --- |
| L6791 |2570 /22965|2026-08-24T12:10:12.999000+00:00|2.074 /12.999|4.687 /[1.0,1.0]|
| L7201 |12595 /112520|2026-08-24T14:58:07.999000+00:00|0.104 /7.999|4.687 /[1.0,1.0]|
| L7351 |15812 /141259|2026-08-24T15:51:44.999000+00:00|2.117 /44.999|4.687 /[1.001,1.0]|

All selected points are unexcluded/not break starts. Keep existing100m/600s,
HDOP<=10,0<neighbor gap<=30s rules, unchanged QC and rounding. Native GPX+real
points only:no interpolation/inverse projection/new coordinates. The private
frozen gpx_audit SHA878ff42ec767e671bf9581ce2d1635c5282ffca469dc6f247654817b7c55779d
reproduced full unrounded matcher dictionaries exactly, not just these displays.

## 4. Shared execution, global preflight and authority boundary

Extend only the reviewed family to load the exact new pin/N=3; reuse the same
shared records-tuple core, one source/CSV crosswalk algorithm and one real GPX
parse. No per-record/night matcher clone or new profile/model/parent/controller.
Preserve caller-owned strict bounded JSON snapshots, all types/digests, exact refs,
new-family pure-time ValueError classification and ordinary callback exception
object identity. Copy each outbound ref and keep saved lineage separately owned.
Caller read_ref MUST verify path/actual bytes/size/SHA (production uses Audit.ref);
ref ownership alone authenticates neither arbitrary callbacks nor source issuer.

Before ANY new-family role is published, validate all policy entries/permutations,
canonical paths and portable aliases, known/missing profiles and ALL ADMITTED
primarySHA+half-open-slice keys, including initial L9654 and protected Aug31.
Duplicate/overlapping slices fail even through another batch/source/transport alias.
No legacy-role downgrade for the family prefix. Poisoned third record, later
invalid entry, duplicate declaration or mutation cannot leave earlier pending
family entries qualified. Legacy Aug31/Sept behavior is unchanged where their
own old inputs/contexts are unchanged. Keep final review/source/descriptor rescans
and existing late-failure boundary; never silently downgrade a contradiction to
missing, unknown-zero, or partial successful qualification.

Use the same supplied context, absolute deadline, input-read ledger and point
counter through discovery/guarded first opens/strict parse/all hashes/real matching/
all rescans/result seal. No private reader/deadline reset/cache exemption. Retain
actual-byte charging and charges for rejected work, bounded sizes before copies,
all-ancestor common local_path/reparse guard and existing namespace restrictions.
No claim of general concurrent adversarial filesystem confinement is added.

Final review keeps the exact dependency schema/authority set:all
FORBIDDEN_AUTHORITY values literal false,independent_device_authentication and
permanent_biological_identity NOT_ESTABLISHED,RESEARCH_EXPOSED,current reviewed_at.
Its verification_profile/family scope,coordinate_method and recovery_class stay
the exact initial-family constants. Only the separate registration stage may
request use_roles=['outcome_label']; software-phase private fixtures are not a
repository registration. The sole additive policy entry is the new capture CSV's
exact {path,size_bytes,sha256,review_ref}; review_ref has exact path/size/SHA.
No separate occurrence/GPX outcome source is added. All old policy semantic
fields,sessions and outcome_coverage remain unchanged. Availability follows the
existing current-audit maximum rule, never an inferred historical receipt time.
Positive-only consistency does not assert active search, completeness, Negative,
prereveal availability, formal metric/science/confirmation/selection/promotion,
training eligibility or production authority. No canonical IDs/old receipts or
old log_byte_exact_native_original_verified=false fields are rewritten.

## 5. Immutable compatibility and expanded input closure

Before implementation, actual initial-family software AND registration exact/fresh
main gates must pass. Normally merge their actual main without Raw conversion;
record the exact base, complete NUL-safe native Git inventory and source closure.
Then capture registered Aug29 direct reproduce_sources/verify_review whole typed
proof/results,input hashes,refs,actual reads/opens/interleaving/points/self receipts
at one recorded fixed verification time using the OLD program BEFORE editing.
Store source capsules/checksums and physical receipts append-only. Test old/new
with identical inputs/clock/context and actual runtime, exact bytes and no exclusions,
tolerances, golden regeneration or fake backend/OS. CI controls must be hermetic.

Preserve exact old Aug31 public/full proof/read/open controls and Sept28 whole
566151B/SHAe1e16caac9986c8d0441dbf1ab4f167aa1907f1d3534dfe61f12efe1fa304904,
its original362 catalog+25 omitted Japanese files plus complete387 catalog proof;
never relabel or overwrite history. Initial Aug29 own six references and descriptor
remain unchanged; its direct API whole artifacts must remain exact under the same
inputs. No extra descriptor reads/proof fields are added to the old Aug31 facade.

ALL ADMITTED is deliberately inspected for global overlap even if a new batch is
NOT yet registered. Appending this pin therefore adds new descriptor metadata
reads/consumed hashes and legitimately changes an existing registered Aug29
family-public audit closure/self receipt. A not-yet-registered descriptor is
expected to add load+final-rescan metadata reads; exact future code must measure
the actual count. Do NOT remove global preflight to force an old audit hash or
rewrite an old golden. Capture expanded-closure results/read ledgers separately,
first without new registration and then with private provisional registration.
The no-family Aug31/Sept fixed-input controls remain separate exact comparisons.

## 6. TDD and actual acceptance gates (not tests run by this design)

- RED first:current exact one-record code rejects this new pin/three-row shape.
  Valid synthetic/hermetic3-row fixtures and the actual native3-source fixture
  must then pass with one GPX parse and all3 row/QC facts,3 event/occurrence count.
- Check valid multi-entry sets, initial+new declaration orders, unchanged N=1,
  poisoned last record/wrong second/third clock/night/source/attribute/count/ID,
  missing/extra/reordered CSV/QC rows,bool/float proof drift and coherently rehashed
  but inconsistent inputs; fail before publishing any pending family role.
- Check duplicate policy/path/case/backslash/dot aliases and missing/unknown/
  downgrade profiles in both orders; duplicate/overlapping primarySHA+slices
  across ALL admissions/protected Aug31,including unregistered descriptors.
- Check source/review/descriptor/CSV size/hash/growth/late mutation, extra or
  invalid refs,borrowed-ref mutation after real verification and returned lineage
  ownership. Do not confuse a byte-verifying trusted reader's contract with
  authentication of an arbitrary reader or issuer.
- Check deadline/read/byte/point exhaustion, cancellation and ordinary caller
  exception identity at early/later callbacks; rejected work retains its charges.
  Final rescan/hash/seal failure leaves no newly qualified source/public units
  through the existing audited failure boundary; no budget reset/partial PASS.
- Use genuine temporary Windows junction/ancestor and POSIX directory-symlink
  fixtures at new capture/occurrence/descriptor/review/root paths:zero external
  payload opens,unchanged sentinels,link-only cleanup. No fake platform/fcntl/FS.
- Execute every old exact control plus meaningful affected regressions. Build a
  COMPLETE native Git snapshot of the actual combined source/input closure,
  verify all files before/after and run the public source auditor once with only
  explicitly listed PRIVATE provisional review/policy changes under existing
  caps. Record actual commit/tree/code hashes,source manifest,consumed hashes,
  checks/units/occurrences/read bytes/points/order/time/self+physical receipts.
  This is source-only, not parent PDCA or a fit. Unknown samples are compared
  only for the same requested operational night.
- Independent exact-source/data review and actual Ubuntu exact-head/fresh-main
  CI must pass; root owns normal merge,new source freeze/STATE and later gates.
  Only a separate root-authorized registration stage may create a NEW final
  review at actual current time and append the sole policy entry. No final
  review/policy publication is part of the software phase or this design.

## 7. Capacity evidence and remaining gates

STRUCTURAL ESTIMATE, not a real future PASS:the actual48d private provisional
8-event/9-occurrence ledger requested Aug29 measured581 reads369038838B338929
charges/18.250s under300s/512MiB/4000reads/1Mpoints. Its619 UNKNOWN is Aug29-only;
old Aug31's688 UNKNOWN is a different cohort, not a demonstrated reduction.
The limited private3-record native reproduction measured17203178B/21246 parsed
points/1.657s (parse0.625s,matches0.406s), not an integrated auditor runtime bound.

The observed admission delta was5capture+5occurrence+2GPX+2TXT+2byteproof+2owner+
4review+3descriptor=25 reads. Shared new GPX/primary reads add11531942B; reserving
128KiB each for two new CSVs/review/descriptor with those multiplicities,plus a
4096B policy increment read twice,gives structural added13768358B and projected
**606 reads382807196B360175 point charges**. Future exact fixed artifact sizes
must stay within this small reviewed envelope; this neither raises existing caps
nor grants an arbitrary max-size input. The one21246-point parse is shared across
three rows. Actual latest-main/initial-registration/expanded-closure input costs
must be remeasured before acceptance; ALL metadata/scans/rescans count. No caching
exemption,cap increase,partial successful output or proven300s hard-preemption
claim follows from this estimate. Real shared-context code stays cooperative,
and the unchanged matcher/underlying calls are not globally preemptible.

Until root/V approve this design and initial software+registration gates pass,
status remains DEPENDENCY_PENDING_SOFTWARE_AND_REGISTRATION. This one-file design
commit grants no runtime/test/data/policy/STATE/workflow/security change permission.
