# Closed legacy backend profile fixture isolation

Author base: `d2f8c759ad9817cdcafab4c97c4fbdf5f4fb08b3`.
Branch: `codex/backend-legacy-adapter-fixture-20261025`.

The positive backend emission fixture exercises a closed historical profile:
the checksum-bound pre-v4 parent and its exact Stage1 source adapter. Reading
the adapter from current HEAD mixed the historical parent with future additive
adapter APIs. A legitimate source change must remain unmapped to the runtime's
closed legacy profile; it must not redefine the historical positive fixture.

This change stores the actual native-LF Git blob from
`5d4b84f:src/evaluation/stage1_source_adapter.py` as readable test code in
`tests/fixtures/stage1_source_adapter_388bf18.py.txt`. The same blob was verified
at historical base `be045334a5ede3d5b92088e86b2b4852ccc8b6a1`
and author-base HEAD. Identity:37345 bytes,
SHA256 `388bf18b1f4f90fb29d48fe0c4f58579bae925d281f99b27eb0e79baa038ada6`.
The helper checks both size and SHA every time it supplies the capsule. Reading
as UTF-8 text restores the code fixture's canonical LF after Windows checkout;
this does not normalize runtime inputs or any original data.

Unit `source_files` now takes ADAPTER bytes from that capsule. The genuine
POSIX engine fixture also overwrites its copied adapter with the same verified
capsule alongside the already-pinned old parent, before its actual Git commit
and push. Schemas, actual transport/checkpoint/restart paths, runtime
`PROFILE_REFS`, current reviewed-v4 admission, unknown-profile rejection and
all authorization flags are unchanged. No runtime source is modified.

At the author base, HEAD still contains that exact historical adapter, so no
current native failure is claimed. The isolation prevents a subsequent reviewed
additive adapter export from changing this positive legacy fixture; actual new
adapter/profile mismatch evidence belongs to that integration review.

## Verification

- Before change: existing16 methods,14 PASS/2 genuine POSIX-only skips,
  native Windows Python3.12.14,92.153s. No fcntl facade or simulated backend.
- After change: the same existing16 methods,14 PASS/2 genuine POSIX-only
  skips,93.131s. Positive legacy mapping, unknown-source rejection and the
  reviewed-v4 ALREADY_IMPLEMENTED case retain their original assertions.
- Both actual POSIX engine tests remain mandatory in Ubuntu CI; a native skip
  is not an engine acceptance result. No admitted development jobs, execution
  authority, source attestation or production status is granted.

Independent exact-source review is pending author release.

The Independent review section is reserved for the reviewer.
