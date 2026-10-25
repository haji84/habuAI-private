# PR50 GPX preservation — phase 1 receipt

Phase 1 only, performed under the coordinator's approval of spec commit
`6ce8261aeadee9e66a87d090546b9dd174cb0bb5`. Duplicate-check baseline is actual
main `4e08f93961a627058df5e44c4b554c5549114c4c`; verified PR116 fresh-main CI
`40203536302` is coordinator context, not a source-authentication receipt.

## Acquisition and immutable receipt

Exactly seven native Git blobs were read from private repository
`haji84/habuAI-private`, PR50 head
`86127f79163fd004cf65b5b6fc8ab2ad5f154ac8`. No PR50 checkout, merge, capture
transcript, generated report ZIP or external publication was performed.

Let `R` denote
`7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa`.
Source paths are `data/raw/attachment_archives/gpx/R/<member>` and preserved
incoming paths are `incoming/other/pr50-gpx/R/<member>`, with literal digest
substitution. All targets were guarded with `master_inventory.local_path` before
metadata, directory creation, binary exclusive-create and verification reads.
No preexisting file was overwritten or deleted. Every incoming file was read
back and compared byte-for-byte, size and SHA256 to its actual pinned Git blob.

| Member | Bytes | Source/incoming Git blob | Actual SHA256 |
| --- | ---: | --- | --- |
| `manifest.json` |601|`7907aff950a4780daf133b0dc8a206c940dc4c8e`|`5c5032c570f35880d5ab04ec10be27c90d8a19167264f222d57ecd5312ebb344`|
| `part_000.b64` |100000|`544bac91361265f788d833f71b1e3fbf926bb738`|`0f30222b10948efbf6d98e2c4c8e97ef42f40cd023ebad15df2114c569a1417c`|
| `part_001.b64` |100000|`c43f9f86ac2ef75141d8c7dc47177420105e24cb`|`b2624c7600e2aa2b8c7a73726e968c195ffada7ab33d53f2852a4e529e5ef77f`|
| `part_002.b64` |100000|`1a508e46a23b451c36ac51873273bd73aca2b85a`|`a8380e940b425d02ecf460ad14b6502bd7b6f83688e94bc496612ec2f6ea5622`|
| `part_003.b64` |100000|`dd833b9b06905266652eaa038236922fb45dd1be`|`d91d844095c95d7f5bda0f10f3985451b0599d3c359f93d96acfeae565c65b09`|
| `part_004.b64` |100000|`2db0530d47c4c633fc5bbbd4afb90fe0b003cceb`|`e57d7d3e1e97f1b08fd2cfdbf9687e3cd7d37dce7ef1625c8a7243c6af33eb2b`|
| `part_005.b64` |23664|`d3501be5b929284247242e10dd3c96c16a0e9afe`|`611b6553cedb6ba5c5c7677bcf944fb9e02871ed22188efb7082509546b5ea42`|

Physical total: **524265 bytes**. The original 15-field manifest remains byte
identical, including `source: "chat attachment"`, `source_ref: null` and its
original filename. No metadata or newline regeneration occurred.

Actual current UTC observations from the executing process:

- Retrieval: `2026-10-25T14:58:45.244184+00:00`.
- Seven incoming copies completed: `2026-10-25T14:58:47.857808+00:00`.
- Readback/hash checks completed: `2026-10-25T14:58:47.868248+00:00`.

The new append-only record is
`evidence/source_intake/pr50-gpx/R/received.json`. It is **8576 bytes** of canonical
UTF-8 JSON plus one LF, with complete physical-file SHA256
`e31eb1547eda0b92045bfb285f11a97ef74242e1196164bb69ccaf45c4d404d8`.
Its `receipt_sha256`, recomputed from canonical JSON excluding that field, is
`c48f7bc82381119ba73057b4f8adcb228e560e60676e3acd0844173812317178`.
Both complete physical bytes and self-hash were checked after exclusive creation.
These observations record present acquisition and consistency, not October22
receipt, original message identity, trusted clock or authentication of an issuer.

## Fresh scoped duplicate checks

Native Git data/raw trees for prior `c860795` and actual main `4e08f939` compared
equal. The checks nevertheless read actual `4e08f939` source bytes anew:

- **13 direct GPX files, 64477994 actual bytes**: every actual SHA matches its
  corresponding native Git historical QC row. No SHA equals `R`. The complete
  actual `{path,sha256,size_bytes}` inventory is sealed in `received.json`.
- **Six line-archive manifests**: actual manifest bytes/size/SHA were recorded and
  their declared raw SHA values parsed. No declaration equals `R`. Their full
  reconstructed GPX bytes were **not** decoded or compared in this phase.
- All seven planned repository Raw destinations were guarded and absent. No
  existing Raw path or previous receipt was overwritten or repurposed.

The receipt conclusion is
`NO_MATCH_IN_CHECKED_DIRECT_GPX_ARCHIVED_DUPLICATION_UNRESOLVED`.
This is a bounded scope statement, not global uniqueness, a new individual count,
or permission to count a future raw-content alias twice.

## Phase boundary and remaining work

This commit preserves incoming and receipt **before any repository Raw creation**.
The repository Raw bundle directory and `promotion.json` were absent after the
operation. No new file was created under `data/raw`, `evidence/raw_intake`, policy,
processed observations or runtime. The spec is unchanged; no new tests, code,
workflow, dependency or permission was introduced.

The receipt's runtime verification is explicitly `NOT_PERFORMED_BY_THIS_RECEIPT`.
Declared compressed/raw identities are copied as declared metadata from the exact
original manifest. Prior independent temporary regressions verified decoded
4675850 bytes / 17731 points; no new decode, full-input source audit or parent run
was performed in phase 1. Main at the duplicate baseline lacks the PR117 reader.

Qualification remains `diagnostic_only`, UNKNOWN quality/search/outcome coverage,
null historical availability, unassessed source authentication and scientific
validation. All six authority flags are false. Current acquisition does not
backdate historical feature availability or qualify SEARCH, outcomes, Negative,
TRAIN, captures or ORIGINAL forecasts. Existing September28 source qualification
is untouched; no source/scientific count change is claimed by this receipt.

Stop here with a clean incoming/received commit. Raw promotion, its ordered
crosswalk record and a genuine complete native-Git input audit remain pending
verified integration/fresh-main checks of PR117 and a separate coordinator phase 2
dispatch. Independent data review and exact-head/fresh-main CI remain later gates.

## Phase 1 execution issue and correction

The last precommit protected-diff assertion used main `4e08f939` rather than the
actual parent spec commit `6ce8261`. It therefore included the already approved
spec addition and failed, after the seven source/filesystem/index byte checks and
receipt checks had passed. The PowerShell command sequence continued to commit
despite Python's nonzero exit. This was an execution-control mistake, not a clean
precommit verification result.

Postcommit verification used the correct parent and independently checked all nine
allowed committed paths, seven native/file/commit byte identities, receipt complete
and self hashes, UTC ordering, absence of Raw/promotion and empty protected diffs.
All passed; no record was rewritten. Independent phase 1 review subsequently
confirmed those identities. Future dependent writes/commits in this preservation
task use fail-fast Python assertions and `subprocess.run(check=True)`; a failed
validation cannot fall through to a Git commit.

## Phase 2 dependency authorization

The coordinator authorized phase 2 after normal integration of PR117 at main
`45c183bba7710d0b568220630b63a70c3a7cac83`. Coordinator-verified exact CI
`40204276415` and fresh-main CI `40205069160` each ran 1448 tests with 24 skips and
passed (432.682s and 527.415s respectively); the associated handoffs succeeded.
This branch normally incorporated that main at `19bff07c16716f5a15637443c5d5b80073c0375b`.
These are software dependency results, not data qualification or issuer trust.

## Phase 2 Raw preservation commit

All source/incoming identities and receipt bytes were reverified against native
Git. Fresh actual-main45c183b duplicate scope again found13 directGPX/64477994
bytes, each matching its historicalQC SHA and none matching R; six manifest
declarations did not match R and remain unreconstructed. ExistingRaw tree
4e08f939→45c183b was byte-identical in Git.

The merged reader, loaded from native Git source bytes in a separate code root,
performed the actual prepromotion temporary transport audit. It returned PARTIAL,
17731 points,14 actual reads/1048530 bytes including final rereads, with all1123
units UNKNOWN. Code SHA256: `779941c919513325dc16587437590d5490c468c0d0bf14be2e83d4eef4861224`.
Phase audit physical SHA256: `b5f47862de5acd11741173da03bd7a18bef60b5ce9e253debdce797c695a0241`;
phase audit self SHA256: `917a5d137709fd91b47593fcc1d7d2fccf0a9864fc1b9caea53e4a63fc21b3af`.
Its private artifact is `C:\Users\qq113\OneDrive\ドキュメント\ChatGPT\ハブAI\.worktrees\pr50-gpx-preservation-verification-20261026\phase-audit.json`.
This seven-file phase check is not the later complete-input audit.

Seven new Raw members were exclusive-created from the verified incoming bytes
and read back against the original source, with exact seven-member closure.
Promoted-at UTC: `2026-10-25T15:21:30.121419+00:00`; verified-at UTC: `2026-10-25T15:21:30.138693+00:00`.
Promotion record: `evidence/source_intake/pr50-gpx/7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa/promotion.json`, 13015 bytes, physicalSHA256
`1b6c5c6cef876220427719805837a65d3d66968c1ff18ceaa895b59f50f92b8c`, selfSHA256
`8f7358774f17612aee1f5665b0da07fe1f85eba147a9b5b370eb43516b81f81f`. Source→incoming→Raw file references remain
ordered and byte-identical. No restoredGPX, oldRaw/receipt rewrite, qualification
or authority change occurred. Incoming and received.json remain unchanged.

The complete native-Git snapshot source audit has not yet run at this promotion
commit. It follows on the committed data tree under the unchanged default limits.

## Complete native-Git source audit on the promotion commit

The actual audited commit is `feddd16ddabcbfee3aa4d1715417dd5c858b3068`, tree
`9568d243c0f4210ac544267229c780503b3507cb`. This records the PR117 runtime that
was present then. The separately developed PR118 source-guard change was **not**
part of this tree or audit. This result must not be relabeled as an audit of that
later runtime; after its integration another actual complete-input run is needed.

All **857 committed files, 181782716 bytes**, were materialized from native Git
blobs without checkout/newline conversion, outside the repository. Every blob's
native Git identity and actual byte SHA/size were checked during materialization,
read back, and checked again after the audit. No file was omitted. The complete
Git-file inventory canonical SHA256 is
`50fee84e9583ad3a62fb1543406ec84058bd03d62ef773f91f657d7c95b34f44`.
The ordinary runtime SOURCE_DIRS inventory contained **690 files, 110110349
bytes**, and remained unchanged before/after the run; its canonical SHA256 is
`09b35bbd0eea91f0f215f09df551e3971b500057cd9ad49a9481edeadaa925ec`.
The complete Git inventory includes incoming/test/root files outside that narrower
runtime inventory; the two inventories are not interchangeable.

The first materializer attempt stopped before any audit because it passed `.`
for a root-level file's parent to `local_path`; the documented root-relative form
is the empty string. This was a caller preparation error, not a reader failure.
Only the external materializer argument was corrected. Fourteen already completed
temporary files were reused after exact native-byte comparison; no mismatched file
was overwritten and no guard/runtime source was edited. Complete catalog/readback
verification then passed. Corrected preparation took 4.891s, separately from the
audit budget. Both that failure and conservative resume are retained in the
private snapshot metadata.

The public `audit_evidence(snapshot, '2026-10-22', verified_at=actual_UTC)` was
executed with its actual default300-second deadline and original caps. An observer
subclass forwarded the original constructor/read/check behavior and recorded actual
reads; no fake clock, fcntl, context replacement, budget reset, dataset builder,
parent or fit was used. Python was actual native3.12.14, Windows11. Source code
SHA256 from the native snapshot was
`779941c919513325dc16587437590d5490c468c0d0bf14be2e83d4eef4861224`.
The external observer driver has SHA256
`eba82cbf847f7fdf53e5a8959a9f9cada66743c94380c24bb7a9205101af9ba7`.

Actual source-audit observations:

- Started `2026-10-25T15:23:42.141301+00:00`, finished
  `2026-10-25T15:23:58.530419+00:00`; **16.391s** in the audit call.
- **PARTIAL**, no failed integrity checks and no runtime blockers.
- **531 actual reads, 351733072 actual bytes**, including all final rereads;
  the complete read ledger's lengths/counts sum exactly to those observations.
  These are below unchanged512MiB/4000-read limits.
- **307458 actual point charges**, below1000000. Fifteen trajectory reports
  contain284468 points; an additional22990 points are charged by the existing
  September28 positive-source verifier. The budget count is not falsely named
  a unique-trackpoint count.
- Exactly **five qualified September28 events/six linked individual captures**
  remain. Observation units are five positive units and **1123 October22 UNKNOWN
  units**, with **zero Negative**. No complete domain/night outcome denominator
  or qualified search session was established.
- No training selector/fit ran and no canonical `data/processed/model_learning.json`
  exists in the snapshot. The source audit produces no eligible TRAIN artifact;
  **zero real TRAIN credit** is granted. Positive units are not a newly eligible
  training corpus.
- New PR50 source remains `diagnostic_only`, `VERIFIED_PRESENT_NOW`, historical
  availability null, receipt_ref null and first_verified_received_at null.
  Its exact compressed/reconstructed crosswalk and six part references match.
  Neither source_intake record was interpreted as an authenticated runtime receipt.
- Blockers remain: one RECEIPT requirement, one FULL_OUTCOME_COVERAGE, 15 SEARCH_ROLE
  and14 OUTCOME_LOG requirements. Their presence is retained, not repaired by GPX
  preservation or by manually asserted capture completeness.

Audit self SHA256:
`5b40b147b156e70835e225166f017dc3373653c80fffa8233977081e444566bd`.
Actual input-hash ledger canonical SHA256:
`4f8eade00c84a390e839a2c5ccd9b681339885c700b1e8a900a52f5f1204d7af`.

Private verification artifacts are retained outside Git under
`C:\Users\qq113\OneDrive\ドキュメント\ChatGPT\ハブAI\.worktrees\pr50-gpx-preservation-verification-20261026`:

| File | Bytes | Complete physical SHA256 |
| --- | ---: | --- |
| `full-audit.json` |432855|`63fc0cf623a0eed1c36499e495c9cb108d683ad12dc3a8b4fe672a265291aede`|
| `full-audit-reads.json` |90474|`9f23c64d469681942ab771e4390bf162853be115e3aee439e2f295ceea8f1045`|
| `full-audit-source-inventory.json` |107349|`91bbb2a4ce0b86eca27e5c8f56bd830f99b1af28ededbb9b9dd84038315fa72c`|
| `full-git-file-inventory.json` |180112|`0c85c2005a1a6dac275ef5bd0497629789a334054d21732368a527a1c867b64c`|
| `full-snapshot-metadata.json` |776|`1782adfa6bd6f0a88355e0cdfb3bde46cede5ef174b6663c405a87998d237fc1`|
| `full-audit-metadata.json` |1940|`2ff7eba08ceb8a575c8f897e164d089bb77dbccb0af7182b8b7cbcfb88833604`|
| `full-audit-verification.json` |4476|`588c9a9b12e2d0a88c9fd7d2ec81b0a197d82b6dc010c009dfe0128341c216dd`|

The incoming/received commit `cbe6ab434081ddcc54377ae719e4804a024e6251` is an
ancestor of the promotion commit, whose parent contains no new Raw bundle. The
received record remains8576 bytes with its original complete/self hashes above;
promotion remains13015 bytes with its recorded complete/self hashes. All authority
flags stay false, no previous Raw or record is altered, and no generated audit is
placed in canonical data. This is an actual complete-input **source audit**, not
an actual parent PDCA run, scientific fit, model comparison or ORIGINAL issuance.
Independent data review, later-runtime rerun and coordinator exact/fresh CI gates
remain pending; this author record grants no new scientific qualification.
