# PR50 GPX byte preservation — independent review

Reviewed 2026-10-26 JST, exact worker HEAD
`6103627e734e486f3d56bf52428a0093106e31e8`. Scope is the approved preservation
spec `6ce8261aeadee9e66a87d090546b9dd174cb0bb5`, immutable records and the
recorded complete-input source audit. This is not source-role/scientific approval.

## Disposition and bounded scope

PASS for the seven-file preservation, record consistency and actual **PR117**
runtime audit evidence reviewed here. New central-read-guard PR118 was absent
from the audited promotion tree. A genuine complete-input audit after that
runtime's integration, coordinator data PR/exact-head/fresh-main CI and normal
integration remain separate pending gates. This review does not substitute a
result from an older runtime for that later verification.

Relative to actual main `45c183bba7710d0b568220630b63a70c3a7cac83`, the complete
diff is exactly 18 additions: seven incoming members, the corresponding seven
Raw members, received/promotion records, approved spec and author review. No old
Raw identity/mode changes, generated GPX, canonical capture/individual row,
legacy raw-intake receipt, policy, model, runtime, test, workflow, old cycle or
permission change is present. PR50 itself and its manual transcripts/report ZIP
were not merged. The source header's filename remains declared provenance.

## Native identity and ordered records

Pinned private PR50 source is
`86127f79163fd004cf65b5b6fc8ab2ad5f154ac8`, archive raw SHA256
`7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa`.
The exact manifest plus six parts total **524265 physical bytes**. For every
ordered member, independently read native source Git bytes equal incoming and
Raw filesystem bytes, index bytes and committed blobs/mode100644. Both actual
directories have exactly those seven members. The 601-byte original manifest
retains its 15 fields, original filename, `source='chat attachment'` and null
`source_ref`; it was not regenerated or given an invented attachment identifier.

| Immutable record | Physical bytes | Physical SHA256 | Self SHA256 |
| --- | ---: | --- | --- |
| received.json | 8576 | `e31eb1547eda0b92045bfb285f11a97ef74242e1196164bb69ccaf45c4d404d8` | `c48f7bc82381119ba73057b4f8adcb228e560e60676e3acd0844173812317178` |
| promotion.json | 13015 | `1b6c5c6cef876220427719805837a65d3d66968c1ff18ceaa895b59f50f92b8c` | `8f7358774f17612aee1f5665b0da07fe1f85eba147a9b5b370eb43516b81f81f` |

Strict duplicate-free finite JSON, exact field sets, canonical UTF-8 plus LF,
full physical refs and self-digests excluding only `receipt_sha256` pass. Both
records and all incoming files are unchanged after their respective commits.
Promotion's ordered source/incoming/Raw refs bind actual SHA/size/Git blob IDs,
and its received_ref binds the full received file rather than its self-hash.

Phase1 incoming/received commit
`cbe6ab434081ddcc54377ae719e4804a024e6251` precedes promotion commit
`feddd16ddabcbfee3aa4d1715417dd5c858b3068`. The promotion parent is the normal
main117 dependency merge `19bff07c16716f5a15637443c5d5b80073c0375b`, which has
no new Raw bundle or promotion record. The later `6103627e` changes only the
author review. Actual receipt chronology remains:

- Retrieved `2026-10-25T14:58:45.244184+00:00`.
- Incoming copies complete `2026-10-25T14:58:47.857808+00:00`, verified
  `2026-10-25T14:58:47.868248+00:00` (Oct25 23:58 JST, before rollover).
- Raw copies complete `2026-10-25T15:21:30.121419+00:00`, verified
  `2026-10-25T15:21:30.138693+00:00` (Oct26 JST).

These are recorded current observations, not trusted issuer clocks or an Oct22
historical receipt. The received record still truthfully says runtime verification
was not performed by that receipt; later promotion/full-audit evidence is separate.

Fresh native-Git duplicate scopes in both records agree: all 13 direct GPX files,
**64477994 bytes**, were independently hashed without an R match. Six actual
line-archive manifest physical hashes and their declared raw SHA values also
match the records, with no declared R. Those archives were not fully reconstructed;
`reconstructed=false` and unresolved global/archive/semantic duplication remain
explicit. This is not a global uniqueness or independent-search certificate.

## Complete private audit evidence

The audited promotion commit is `feddd16ddabcbfee3aa4d1715417dd5c858b3068`, tree
`9568d243c0f4210ac544267229c780503b3507cb`. Independently streamed actual Git
blobs through `git cat-file --batch` and compared every one to the physical
snapshot: **857 files, 181782716 bytes**, exact path closure, modes and hashes.
This is native data identity, not working-checkout CRLF recovery.

Complete Git inventory canonical SHA256:
`50fee84e9583ad3a62fb1543406ec84058bd03d62ef773f91f657d7c95b34f44`.
The narrower ordinary SOURCE_DIRS inventory is **690 files/110110349 bytes**,
canonical SHA256
`09b35bbd0eea91f0f215f09df551e3971b500057cd9ad49a9481edeadaa925ec`.
The two inventories have different scopes and were checked separately.

All seven private full-audit artifact physical sizes/hashes match the author
review, including complete audit, read ledger, both inventories, snapshot/run
metadata and verification record. Their actual JSON/canonical seals were parsed,
not accepted from the author summary. Existing driver bytes also match recorded
SHA256 `eba82cbf847f7fdf53e5a8959a9f9cada66743c94380c24bb7a9205101af9ba7`;
its observer forwards the real constructor/read behavior and invokes the public
auditor with default limits. Its output artifacts remain outside canonical data.

Actual `full-audit.json` physical SHA256:
`63fc0cf623a0eed1c36499e495c9cb108d683ad12dc3a8b4fe672a265291aede`;
audit self-digest:
`5b40b147b156e70835e225166f017dc3373653c80fffa8233977081e444566bd`;
214-input-hash ledger canonical SHA256:
`4f8eade00c84a390e839a2c5ccd9b681339885c700b1e8a900a52f5f1204d7af`.
Every one of the 531 read-ledger entries matches actual native/snapshot SHA/size;
the lengths sum to **351733072 bytes**, including final rereads. The recorded
**307458 point charges** consist of 284468 trajectory-report points plus 22990
existing Sept28 verifier charges, not 307458 unique new observations.

The 85 Python runtime files hash to
`779941c919513325dc16587437590d5490c468c0d0bf14be2e83d4eef4861224`.
The separate materialized code inventory has 87 physical files because it also
includes one shell and one PowerShell script. Auditor identity is PR117's
44386-byte/SHA256 `2ae896d4e95094d9d0edcc1bdc18d97059e7bf4d547ad0e415c3a6ac2f1889ab`,
not PR118's new `cb8e9a99...` auditor. Promotion reader code refs and actual
snapshot bytes bind that distinction.

## Independent actual replay

In addition to artifact/native-byte verification, independently invoked actual
`audit_evidence` in the complete native snapshot on native Python3.12.14/Windows,
with actual current verified_at and unchanged default300s/512MiB/4000-read/1M-point
limits. No fake OS/fcntl/context, new output artifact, parent or fit was used.

Started UTC `2026-10-25T15:38:59.475489+00:00`, finished
`2026-10-25T15:39:13.802364+00:00`, **14.313s** actual audit duration.
Result: **PARTIAL**, no failed integrity checks, **531 reads/351733072 bytes/
307458 point charges**. All 214 input hashes and requirements exactly match the
recorded run; source inventory remains unchanged. New ephemeral audit self-hash
`4bf90aef6a00b4e40a5b31bd4c5cdeca8a83a99541a1295bbd9edce53ad7c330`
uses the new actual verification time; old artifact/receipt bytes were not rewritten.

Both runs retain five existing qualified Sept28 events/six individual occurrences,
five positive observation units, **1123 October22 UNKNOWN, zero Negative**, and
no established complete denominator. New GPX source remains diagnostic_only,
quality/search UNKNOWN, VERIFIED_PRESENT_NOW, historical availability/receipt_ref/
first_verified_received_at null. Neither source_intake record is interpreted as
an authenticated runtime receipt. No new canonical model_learning artifact or
training selector/fit exists here, so this review grants **zero TRAIN credit**.

## Execution corrections and remaining gates

The author review honestly retains the initial wrong protected-diff baseline and
PowerShell sequence that committed despite Python's failed assertion. Corrected
postcommit checks used approved spec parent6ce8261 and passed; this independent
review rechecked native identities/closure rather than treating that first command
as successful. Received bytes were not rewritten to hide the failure.

The first external materializer's root-parent `'.'` guard error occurred before
any audit; it resumed using the valid empty root-relative path, reusing fourteen
files only after exact native comparison. The private snapshot metadata records
that failure/resume. No runtime guard or mismatched source file was repaired.

This review's first external check also stopped on an incorrect hardcoded87
Python-file assumption; inspection established85 Python plus .sh/.ps1 in the
physical code inventory. Only the outside-worktree check was corrected. Fresh
full check PASS8.172s; the code hash itself matched throughout. External checker
`.worktrees/pr50-preservation-independent-checks-20261026.py`, physical SHA256
`64d1fccf4f7434666bf2a2fd811fa139dedcb59179fd4617711d3a0b41a70264`.

All six authority flags remain false and source authenticity NOT_ATTESTED. No
historical availability backdate, SEARCH/complete-outcome qualification, individual
identity generation, official forecast, model fit/selection, untouched confirmation,
production or master completion is claimed. Source consistency and file placement
do not authenticate an issuer or complete a scientific denominator. Existing
common-helper metadata/other-enumerator/non-atomic limitations are not repaired by
this data-only branch. PR118 integration/current-runtime rerun and coordinator CI
remain required before this older-runtime evidence can be supplemented for release.

## Current PR118 runtime follow-up — independent PASS

This addendum reviews audited data commit
`731799d3b0745444108ed95459f396278d5957f9`, tree
`fd22a4d7fabaed28f5afe309ea130814f28612e9`, after normal integration of actual
main `c0428722f03e6fd06641bd61c3b4f060d76da0ac`. The preceding PR117-specific
review and its artifacts remain historical records; they were not relabeled.
The separate author follow-up `86113be0fed675631d20a6d908fa7802d6130eaa` adds
only76 author-review lines and accurately distinguishes the two executions.

Independently streamed all **863 native Git blobs/181863818 bytes** through
`cat-file --batch`, matching every committed path, mode, blob ID, SHA256/length
and actual private snapshot file. No checkout newline conversion or omission.
Complete native inventory canonical SHA256 is
`8200e3f89f866524de3abdb2ce7de4c6e03a47fe12610cb88144416616a81401`.
Runtime source inventory is independently **695 files/110175311 bytes**,
canonical SHA256
`bdc2f08c06ef8ee258a9dd378ed6b80532ea05fb893c6fdf742949f5f211b342`.

All eight artifact refs in the new private `artifact-summary.json` were checked
against actual files. Their canonical JSON, full audit self-digest and every
read-ledger entry match the native inputs. The directory is the prior private
verification directory's `after-pr118-731799d3` subdirectory. Key identities:

| Artifact | Bytes | Physical SHA256 |
| --- | ---: | --- |
| full-audit.json | 432855 | `2b1c4e6ce3c14a90548fdd30639c37d1f161750a6edf27f1afe6bcd1d2d0b2c2` |
| full-audit-reads.json | 90474 | `9f23c64d469681942ab771e4390bf162853be115e3aee439e2f295ceea8f1045` |
| full-audit-verification.json | 6421 | `74a2baa83ed099fd6d272f5cc0431df4892fc4542af769e1d3d36709fbaeec4a` |

Recorded actual audit self-digest:
`b8c8f242e88c3dbb5583799c86e32d972f3db565c77ab87450de79cfb5f938d9`.
The 85-Python runtime code hash is
`548de6fd06b48ff78d4b917e394e429b86b7912f3a002556db1c7df075281e92`.
The actual native auditor is the reviewed 44489-byte PR118 code, blob
`c22f2af32d2a0852de6cb953adb5bb8ed8d68d2e`, SHA256
`cb8e9a99b310b51764bcd74600059fc0c364c405b48307357646332796338515`.
The record's 17.641s is this new execution's reported duration, not the old run's.

A fresh independent actual public-API replay also ran on this new full native
snapshot, current UTC `2026-10-25T15:49:32.267166+00:00` to
`2026-10-25T15:49:48.076644+00:00`, **15.813s**. It used native Windows/Python,
the real current-code API and unchanged default300s/512MiB/4000-read/1M-point caps.
No replacement clock/context, fake OS/fcntl, model, parent or new artifact write.

Result was **PARTIAL**, no failed integrity checks, **531 actual reads/
351733072 bytes/307458 point charges**. All214 input hashes and requirements
match the new recorded audit exactly; source inventory remains unchanged.
New ephemeral audit self-digest with the actual replay time:
`e305a9f3821587048462dee4e0cb88914be84a9b995c8bb21681d6994b1a7789`.
The original private artifacts and provenance records were not rewritten.

The same existing five Sept28 events/six occurrences and five positive units
remain; all1123 October22 units remain UNKNOWN, zero Negative, zero TRAIN credit
and no complete denominator. No source-authentication or authority upgrade occurs.
The new guard changes static path admission without changing these ordinary
reads/counters. Old Raw is unchanged; the seven new Raw members and both
received/promotion records remain byte-identical to their earlier committed
identities. No new canonical model_learning artifact or selector/fit is present.

External checker, outside Git:
`.worktrees/pr50-current-guard-independent-checks-20261026.py`, physical SHA256
`55ffc5ccd66e2383391a0a9ae6bb281ea71a7f89a672ba2b5b42b7d71e16d63b`.
Fresh complete native/artifact checks plus actual replay passed without a new
harness failure. The earlier execution-error narratives remain untouched.

The prior pending current-runtime source-audit review gate is now satisfied for
this exact731799d3 data/code snapshot. Coordinator metadata, data PR/exact-head/
fresh-main CI and normal integration remain separate gates. This source-data
review establishes no issuer truth, complete search/outcomes, historical feature
availability, scientific confirmation, fit, forecast or production authority.
The common-helper metadata/other-enumerator/non-atomic caveats still apply.
