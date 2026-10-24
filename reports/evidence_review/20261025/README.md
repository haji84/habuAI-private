# Lane E execution artifacts

Source revision: `4981592789f5a6fe01800df85105f2d0c49c0b4a`.
Review: `docs/reviews/lane-e-20261025.md`.
Outcome: 75 packets / 99 anchors / 94 candidate bins; UNKNOWN 75, eligible 0.

`eligibility-audit.json` is an audit report, not a training corpus. All labels are
null. `source_reference_integrity=HASHES_VERIFIED` concerns whole-file refs and
membership; source-block interpretation remains with the existing source parser.
The report grants no independent search, outcome-completeness or owner authority.

`source_blob_manifest.json` records exact Git source bytes separately from local
CRLF checkout bytes. To reproduce, materialize its 61 paths using
`git cat-file blob 4981592789f5a6fe01800df85105f2d0c49c0b4a:<path>` into a dedicated
derived root, verifying SHA and size against each manifest entry. Do not rewrite
the working Raw/ORIGINAL files. A text checkout or converted git archive is not
a byte-exact substitute.

Run the existing source audit on that root:

```text
python scripts/audit_august_75_fauna_motion_review.py --root <derived-root> --output <private-output>
python -m unittest discover -s tests -p test_observation_eligibility_v1.py -v
```

Read the generated existing `75_group_motion_review_private.json` and
`99_source_anchor_motion_review_private.json`; call
`observation_eligibility_v1.review_motion_packets(packets, anchors, source_blobs)`.
The byte map uses the existing native log path plus each anchor night's
`data/raw/gpx/<night>__legacy.gpx`. The native log and nine source nights are
listed in the output's `source_manifest`. This reproduces audit SHA
`0a3c873c1ac93f32a83779bd420328f1260a091c3049d65f384dbc3cb2b2446e`.

Committed evidence is limited to aggregate/audit JSON, SHA manifests and test
evidence. Detailed packet coordinates/times, source_blob_snapshot/, the rejected
converted source_snapshot/, and full raw Windows suite output remain runtime-only
and are excluded from this commit. The rejected converted snapshot cleanup was
blocked by automatic command policy; it has no evidentiary authority.

TDD: 11 tests missing API -> 16 failing subtests, no test errors; two additional
strict-count/full-road-flag regressions failed before their fix. Final 13 pass.
Full local suite: 321 tests, 122 errors (85 missing modules,
encoding, source byte mismatch, missing paths); all names and exceptions are in
full-suite-windows-summary.json. Remote Linux exact-head CI is pending the
coordinator; this local run is not a full-suite PASS.
