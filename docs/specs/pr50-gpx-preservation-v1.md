# PR50 GPX preservation v1

Status: design only, awaiting coordinator approval before any data write.
Design base: `4e08f93961a627058df5e44c4b554c5549114c4c`.

## Scope and dependency

Preserve exactly seven existing private-repository GPX transport blobs from PR50
head `86127f79163fd004cf65b5b6fc8ab2ad5f154ac8`, without merging that PR or its
other contents. Follow AGENTS.md: incoming first, immutable receipt with actual
byte/hash/source/time/duplicate status before any new Raw, then an ordered
promotion crosswalk. This grants no new source or model authority.

This document authorizes no execution by itself. The coordinator must approve the
design and later dispatch the data-preservation work. Incoming plus its byte-only
receipt may precede reader integration. Raw promotion and the final complete-input
source audit require PR117's reviewed reader to be normally merged and verified
on actual main. Main at this design base lacks that reader; no final source audit
has been run or passed here.

The later slice is data/records/review only: no new code, dependency, workflow,
policy, namespace, budget, label, capture transcript, report ZIP, canonical
individual, SEARCH declaration, complete-outcome claim or forecast. Coordinator
owns STATE, freeze, CI and PR integration. Keep originals and artifacts private.

## Exact seven-file identity

Let `R` be
`7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa`.
The source prefix is `data/raw/attachment_archives/gpx/R/`, substituting the
literal digest for `R`. Read these exact native Git blobs, not connector-rendered
text, a checkout's newline-translated text, a regenerated archive or a restored
GPX. Preserve all seven original byte strings unchanged:

| Member | Bytes | SHA256 |
| --- | ---: | --- |
| `manifest.json` |601|`5c5032c570f35880d5ab04ec10be27c90d8a19167264f222d57ecd5312ebb344`|
| `part_000.b64` |100000|`0f30222b10948efbf6d98e2c4c8e97ef42f40cd023ebad15df2114c569a1417c`|
| `part_001.b64` |100000|`b2624c7600e2aa2b8c7a73726e968c195ffada7ab33d53f2852a4e529e5ef77f`|
| `part_002.b64` |100000|`a8380e940b425d02ecf460ad14b6502bd7b6f83688e94bc496612ec2f6ea5622`|
| `part_003.b64` |100000|`d91d844095c95d7f5bda0f10f3985451b0599d3c359f93d96acfeae565c65b09`|
| `part_004.b64` |100000|`e57d7d3e1e97f1b08fd2cfdbf9687e3cd7d37dce7ef1625c8a7243c6af33eb2b`|
| `part_005.b64` |23664|`611b6553cedb6ba5c5c7677bcf944fb9e02871ed22188efb7082509546b5ea42`|

Physical total is **524265 bytes**. The native 15-field manifest declares XZ
392748 bytes, SHA256
`23db6564258f4c09d99e974df03cfd0c849c65fe46e6f574cbccd98a8013c592`,
and GPX **4675850 bytes**, SHA256 `R`. Independent temporary reader regressions
parsed **17731 points**; those are previous software evidence, not a current full
input audit. Do not add a trackpoint-count field to the original manifest.

Keep original manifest metadata literally unchanged: original filename
`2026-10-22-0816 タイトルのないトラック.gpx`, source `chat attachment`, source_ref
null. It remains opaque declared provenance. New preservation records must not
replace null with an invented original attachment/message identifier.

## Exact paths and records

Use these new paths, with literal `R` substituted:

```text
incoming/other/pr50-gpx/R/<each of the seven original members>
evidence/source_intake/pr50-gpx/R/received.json
data/raw/attachment_archives/gpx/R/<each of the seven original members>
evidence/source_intake/pr50-gpx/R/promotion.json
docs/reviews/pr50_gpx_preservation_20261025.md
```

Incoming and Raw directories contain only those seven members. Do not add a
restored `.gpx`, hidden receipt, README or repair file inside the Raw archive.
There is no new `evidence/raw_intake` entry. Its legacy `_receipts` scanner reads
leaf files early, before the new guarded trajectory reader; it must not be used
to imply this bundle or its issuer was runtime-authenticated. The new
`evidence/source_intake` records are preserved provenance, not a new runtime
receipt/profile API. Existing audit code does not interpret them as qualified
availability or roles. Incoming is not a master_inventory SOURCE_DIRS namespace.

Records use canonical UTF-8 JSON plus one LF, no NaN/infinite numbers or duplicate
keys. `receipt_sha256` is SHA256 of canonical JSON excluding that field. References
to a record use `{path,sha256,size_bytes}` over its **complete physical file**, not
its self-hash. Record own file identities separately in the review crosswalk.

`received.json` has exactly these fields:

```text
schema_version, status, base_main_commit, source, retrieved_at_utc,
received_at_utc, verified_at_utc, transport, files, duplicate_check,
qualification, authorities, receipt_sha256
```

- Schema is `habu-pr50-gpx-received-v1`; status is
  `PHYSICAL_GIT_BLOBS_VERIFIED_INCOMING_ONLY`.
- `source` is `{repository,pull_request,commit,acquisition,issuer_authentication}`:
  `haji84/habuAI-private`, 50, the exact source head above,
  `EXACT_EXISTING_GIT_BLOBS`, `NOT_ATTESTED` respectively.
- `base_main_commit` binds the actual preservation duplicate-check snapshot.
- `files` is exactly seven entries in the table's order, each
  `{source_path,git_blob,sha256,size_bytes,incoming_path}`. Obtain Git blob IDs
  and SHA256/size from actual pinned bytes, not filenames or a copied assertion.
- `transport` is `{physical_size_bytes,declared_compressed,declared_reconstructed,
  declared_original_filename,declared_source,declared_source_ref,
  runtime_verification}`. The two declared identities are `{sha256,size_bytes}`;
  all values agree with original manifest bytes. Runtime verification is
  `NOT_PERFORMED_BY_THIS_RECEIPT`. A previous independent decode is cited only in
  the separate review, not relabeled a new live or complete-input run.
- Duplicate/qualification/authority objects are defined below. Every observed
  timestamp is actual UTC acquisition/verification time; receipt creation follows
  all incoming writes and hash checks. Do not backdate to October22 or the PR date.
  `retrieved_at_utc` records this retrieval; `received_at_utc` records completion of
  the seven incoming copies; `verified_at_utc` follows their checks. These times
  attest the operator's current observations, not a trusted issuer clock.

`promotion.json` has exactly these fields:

```text
schema_version, status, base_main_commit, received_ref, source_commit,
reader_dependency, promoted_at_utc, verified_at_utc, transport, files,
duplicate_check, qualification, authorities, receipt_sha256
```

- Schema is `habu-pr50-gpx-promotion-v1`; status is
  `EXACT_TRANSPORT_PRESERVED_AS_RAW_DIAGNOSTIC`.
- `received_ref` is the immutable full-file reference above; `source_commit` is
  the pinned PR50 head. `base_main_commit` is the actual promotion baseline.
- `reader_dependency` is `{main_commit,source_commit,code_refs}` identifying the
  merged reviewed PR117 implementation and actual reader/auditor bytes used for
  the prepromotion temporary transport check. It is source identity, not issuer
  or scientific authentication.
- `files` is seven ordered `{source_ref,incoming_ref,raw_ref}` entries.
  `source_ref` is `{commit,path,git_blob}`; the latter two refs each use exact
  physical `{path,sha256,size_bytes}`. Corresponding incoming/Raw bytes must both
  equal the source table, not merely equal each other.
- `transport` is the existing guarded reader's exact verified transport crosswalk
  from a temporary validation root containing those seven incoming bytes at its
  native `data/raw/...` layout. Its paths denote that explicit temporary layout;
  the ordered file crosswalk binds them to actual incoming/Raw paths. No output
  GPX is written. This is phase transport verification, not a final whole-source
  audit or proof of historical receipt.
- `duplicate_check` is a fresh prepromotion check, not an assertion that the
  earlier received record remains current. Promotion/verification UTC times are
  observed after the Raw copy/verification, never inferred from the GPX.

## Duplicate scope and limitations

`duplicate_check` has exactly
`{snapshot_commit,destination_status,direct_gpx,line_archive_declarations,conclusion}`.
`destination_status` records absence or byte-exact existing matches for each of
the seven destination paths; any mismatch is a hard stop.

`direct_gpx` is `{status,inventory,total_size_bytes}`. Its inventory is all actual
direct GPX file refs in that immutable main snapshot, with actual bytes and hashes
compared to decoded `R`. V's prior c860 audit checked 13 files, **64477994 bytes**,
with no matching raw SHA. That is a prior scoped observation. Recheck actual
execution snapshots; do not silently carry these counts forward if files change.

`line_archive_declarations` is `{status,manifest_refs,reconstructed}`. Previous
review saw six legacy manifests with no matching **declared** raw SHA and did not
fully reconstruct them. Set `reconstructed=false` unless a separate actual bounded
reconstruction is performed. Preserve actual manifest refs and the precise
`NO_MATCHING_DECLARED_RAW_SHA` status; do not turn it into verified raw uniqueness.
Do not broaden this preservation task into reconstructing all legacy sources.

Conclusion is `NO_MATCH_IN_CHECKED_DIRECT_GPX_ARCHIVED_DUPLICATION_UNRESOLVED`
when those limited checks agree. It is not a global deduplication certificate.
If an actual direct duplicate or conflicting declaration appears, preserve
incoming/receipt and stop Raw creation for coordinator disposition; never silently
append observations, choose one identity or overwrite a source. Exact existing
seven-member Raw transport can be reused only after all identities and closure
are checked and its prior provenance is retained; never regenerate old records.
Any future raw-content alias remains subject to the reader's raw-SHA deduplication
and contributes no duplicate point/effort credit.

## Qualification, authority and availability

Both records carry the same exact `qualification` object:

```json
{"use_roles":["diagnostic_only"],"quality":"UNKNOWN","search_role":"UNKNOWN",
 "outcome_coverage":"UNKNOWN","historical_available_at":null,
 "source_authentication":"NOT_ATTESTED","scientific_validation":"NOT_VALIDATED"}
```

`authorities` has exactly `fit_authorized`, `scientific_execution_authorized`,
`official_issuance_authorized`, `confirmation_authorized`, `selection_authorized`
and `production_authorized`, all false. The word promotion in the record denotes
byte-preservation placement only. There is no model promotion, authentication of
owner wording, original forecast, complete SEARCH or capture-outcome authority.

The runtime continues ordinary `VERIFIED_PRESENT_NOW` availability on a later
audit, not `VERIFIED_RECEIPT` based on these new records. Preserve the current
nullable historical availability; present GPX bytes cannot become a historical
forecast predictor or create an untouched confirmation cohort. Two hand-transcribed
PR50 positives and its generated ZIP remain outside this slice.

## Required ordered execution and immutability

1. After explicit dispatch, confirm clean isolated branch and actual main/source
   identities. Enumerate only the seven pinned source paths. Guard every target
   path with `master_inventory.local_path` before metadata, directory creation,
   reads or writes; reject reparse paths and portable aliases. Use raw native Git
   blob bytes and binary I/O, never `read_text`, pretty-printing or newline recovery.
2. Exclusive-create the seven incoming files. Before reusing any preexisting
   incoming path, require exact source size/SHA. Recheck all seven actual files,
   source Git blob IDs and the bounded duplicate scope. Do not call the current
   single-file ingest CLI: it can create Raw before its receipt and writes the
   legacy leaf receipt namespace, so it does not implement this sequence.
3. Exclusive-create and seal `received.json`. Verify its complete physical hash
   and self-hash. Make a distinct incoming/received-only Git commit **before any
   repository Raw creation**, so this ordering is concrete and reviewable. Keep
   that commit identity in the later review; never update its timestamps on retry.
4. Wait for reviewed PR117 on verified actual main. Normally integrate that
   dependency without copying runtime code from another tree. With unchanged
   limits, verify the seven incoming blobs through the actual guarded reader in
   an isolated temporary native-layout root. Check compressed/raw SHA, decoded
   size and actual17731 points; retain a private phase read ledger. Recheck current
   destination/duplicate scope against the actual new main snapshot.
5. Only then exclusive-create the seven missing repository Raw members from
   incoming bytes. Do not overwrite/delete any existing Raw, receipt or record.
   Read back and compare every member to its pinned source identity. Check exact
   directory closure and unchanged existing Raw inventory. An interruption may
   leave an incomplete new bundle: stop, report it and do not write a successful
   promotion record. Matching complete files may be verified/reused on retry;
   mismatched or partial existing files require coordinator disposition, not
   automatic cleanup or repair. No atomic seven-file transaction is claimed.
6. Once all seven Raw identities and their crosswalks pass, exclusive-create
   `promotion.json`, verify physical/self hashes and seal an independent data-only
   commit. The received record remains byte-identical. This record certifies the
   completed copy/check sequence, not the later complete-input audit.
7. Run the final complete-input verification below; persist its honest review
   independently. Do not mutate prior records to backfill PASS or new times.

Identical existing records are reused only after verification; a conflicting
record is never overwritten. Receipt commits provide recorded ordering and hash
consistency, not authenticated timestamps, durable external attestation or a
trusted transactional publisher. No secrets, capabilities or permission changes.

## Complete-input validation and finish line

Materialize a complete temporary snapshot from actual native Git bytes of the
data commit plus merged PR117 runtime and current source/policy/evidence inputs.
Verify its exact commit/tree and all existing Raw identities; do not normalize
scientific data to accommodate a Windows checkout. It must contain the complete
existing source input tree, not the earlier seven-file-only temporary regression.
Execute actual `audit_evidence` on this snapshot for October22 with the unchanged
default300-second owned deadline, 512MiB actual reads, 4000 reads and 1000000 points
(100MiB per read). Default300 is not a claim that the legacy API validates an upper
300-second bound. No budget reset, fabricated measurements or fake POSIX modules.

Record actual code/commit/tree identities, snapshot inventory SHA, full audit and
input-ledger SHA, physical read counts/bytes including final rereads, point counts,
status/QC/requirements and source crosswalks in the private verification artifact
and review. An ordinary metadata/copy/decode check cannot substitute for this run.
Keep the full audit JSON outside canonical data as a private verification artifact;
the review references its actual identity and location. The generic auditor does
not consume source_intake as issuer-authenticated receipt data; separately verify
both new provenance records and their crosswalks rather than claiming otherwise.

Expected evidence disposition stays September28 **five qualified events/six
individual captures**, **zero eligible real TRAIN** and **zero new Negative**.
Confirm those actual invariants and UNKNOWN-safe October units; if a count differs,
stop and report it. PR50-only software regression's 1123 UNKNOWN units/14 reads/
1048530 bytes is not a predicted full-tree budget or expected whole audit total.

Record actual FAIL/BLOCKED if aggregate reads, source integrity, runtime or
qualification checks fail. Do not increase limits, drop existing sources, alter
Raw, weaken checks or manufacture an audit PASS to finish preservation. Existing
incomplete search/outcomes remain explicit scientific blockers even when software
and byte preservation pass. A complete-input **source audit** is not a full parent
PDCA run, fit, KPI, ORIGINAL issue or production release. Independent data review
and exact-head/fresh-main CI remain coordinator integration gates.
