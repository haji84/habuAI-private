# PR #136 main integration readiness (2026-11-04 JST)

This is a dated pre-merge checkpoint. The owner approved integration into main.
Actual merge SHA and its own fresh-main CI are recorded in the existing
[PR136 status comment](https://github.com/haji84/habuAI-private/pull/136#issuecomment-6612739570).
This checkpoint grants no scientific, private-data-publication or Champion authority.

## Verified repairs before integration

- Restore validates session contents and explicit time offsets before any database
  write. Invalid GPS/count/taxonomy records are rejected. Existing valid backups,
  source strings, revision compatibility and active-session CAS behavior remain.
- JSON backup export and restore share the existing 30 MiB UTF-8 bound. Oversized
  backup export stops before download while the entire local session remains;
  separate GPX/log exports remain available. The 200,000-point boundary was tested.
- Intake stages new inputs and commits source hashes together with successfully
  parsed/reconciled rows. Failed file reads, decoding, size/parse limits and Clear
  cannot mix old approvals with new hashes or resurrect obsolete inputs.
- The build derives the offline cache generation from worker and application-shell
  bytes. Asset-only changes refresh the worker. A failed new installation preserves
  the active generation. Repeated builds have stable generations; build-clock data
  are excluded through the existing fresh-summary protocol. CRLF source is supported.
- Owner zero counts require an integer. Later zero sources cannot overlap excluded
  nights; overlay capture dates cannot exceed the overlay as-of. Malformed source
  restrictions raise the existing source-validation error. No scientific Negative
  is inferred from these owner dashboard totals.

The integrated affected suite is **102 PASS / 0 SKIP / 0 FAIL / 0 ERROR**.
The actual existing dashboard aggregate remains 262. Full repaired-head CI and
fresh-main CI are separate required checks; old a8f7 CI is not inherited.

| Independent review | Private receipt SHA256 |
|---|---|
| cache/build + owner guards | `5ce5229aa248afd8092f38974d1b2c0ae2c30eb5a047b1953df17af4b930068d` |
| restore/export | `c68a39a76b80390eb60ce70e74aaa92a4fd6054b23111259e068b4ce194880b8` |
| additional restore controls | `6fadd6e867be606121bbed05feefd769b95b72bfb3974fff52300b42f8bab95c` |
| intake source atomicity | `010d6d29d578b11b0c3b44ada4b586d1a4b56500f7c7a532d5cd7cb621910244` |

Current code Freeze is cycle122-04: 122 code references + one unchanged policy =
123 inputs, code SHA `5a37d1a41c46803a02c70642b06aba00f798fcd74c44d1b4883cba751fb3de80`.
Cycle canonical SHA `c198ea348cf63cc3b8235c8ce507b1d1f28e9f9c7711d33b7101c097f3940953`;
manifest-file SHA `653a37e7e4f78c55bfab90160d1abb467d0af4e35465a15069bf442238f5ec58`;
cursor raw-file SHA `305dd759a7d5ed1e6fe9c261234e87d937667b403f0049d0086791cf1cb6b289`.
Prior cycles remain immutable. Fit/production model flags remain false.

## Actual sources and remaining gates

The nine native runtime files bound to the real v4 route recovery remain unchanged.
Its 14 distinct GPX sources, 266,737 original fixes and separate 30/17 event cohorts
retain their prior private evidence. No original, canonical tally or model is edited.

Read-only retrieval obtained an older private Drive PDCA text view, staged with its
metadata and byte hashes. This is a connector text snapshot, not a native original
binary or independent search/outcome certificate. Drive access exists; the latest
154 candidate JSON, November 1/3 originals and required legacy model/PDCA bodies
remain unretrieved. Reported Oct26 GPX size/hash and logical Library paths remain
reported references; bounded local lookup found no measured original.

Retrieval audit SHA `bb6f919f97a19dc0cedb13d4def7384ab51047b22e8633ce4d5b20492e7cecff`;
bounded Oct26 lookup SHA `ac09e53d1c49b6855b4e17fef9ea6f8ceeaa60d0a8b68f124db82869534db05a`.
No private contents, location details or private document identifiers are published.

Formal fit rows remain 0, total qualified units unknown/null, and improvement
NOT_EVALUATED. Physical handset, live Access, trusted prospective P0 and actual
field P0-to-PDCA acceptance require their own real evidence. Billing, permissions,
public-release settings and Champion authority are not changed by these repairs.

Existing production Access was separately checked before merge: canonical386
and its actual hash URL redirect all10 anonymous route requests to Access login.
This proves neither authenticated owner operation nor the new deployment.
HTTP receipt SHA `050c064b245ff04ba2d62ff65d694ab9a6ad4b77d94707b1e9c7b69210965c16`;
API receipt SHA `10e1a38a73218ce33a400dcae71ba1cbf0788e58a8be3f83b4fb5d66c0764d54`.
Settings and manual deployment were not changed. The existing protected Git
Integration may run on the owner-approved main merge; post-merge observation is required.
