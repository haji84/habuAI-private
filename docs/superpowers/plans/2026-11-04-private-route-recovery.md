# Private route recovery and capture evidence: bounded implementation plan

Base: existing Draft PR #136, `b762da225f132aa453c3233c6774e2c18b631ac4`.
Specification: `docs/specs/gpx-route-and-habu-reaction-reconstruction-20261104.md`.
Reuse the existing GPX QC/projection, public-road geometry helpers, private intake,
G0 selector, fitter, and promotion rules. No new ML architecture or production authority.

## Design and contracts

- Preserve GPX/log bytes and source order, track/segment boundaries, native aware
  timestamps, quality fields and 07:00 JST nights. Reject malformed structures;
  quarantine local bad points and keep good measured segments on either side.
- Keep measured fixes distinct from bounded linear interpolation, inferred road
  references, activity hypotheses and unobserved gaps. No route across a long
  gap or ambiguous road branch is certified. Unsupported route hypotheses remain
  explicitly unproduced. No universal speed cutoff certifies search activity.
- Partition each accepted adjacent-sample interval at 100m UTM cell and 10-minute
  JST boundaries. Report bracketed/interpolated duration and point counts
  separately; durations are proxies, not continuously measured search effort.
- Explicit source-bound owner pause intervals are clipped, unioned and subtracted
  from effort. A capture stop is not a pause. Retain partial overlap in windows.
- Capture events preserve identity, species, owner/other roles, quantity,
  recorded-time semantics/uncertainty and source digest. Time-only captures stay
  positive evidence. Multiple individuals and visits cannot duplicate an event.
  Match only qualifying GPS samples by BOTH distance and time; never call a match
  predictive success. No automatic official positive/negative qualification.
- Private CLI reads explicit SHA/size-bound manifest inputs only. Outputs must be
  outside Git and append-only, with deterministic content/readback receipts.
  JSON, XML, row, point, output and operation budgets are finite. CLI stdout/error
  messages contain aggregate counts and fixed diagnostic codes only.
- Current-night outcome/route is POST_SEARCH_RESEARCH_ONLY and cannot feed P0
  features. Existing formal selector and model/Champion authorities are unchanged.

## Work and validation

1. Independently audit the new private handoff/fit scripts and latest exact-head CI.
   Locate authorized Nov1/Nov3 private sources through existing connectors. Record
   missing access precisely and use older authentic local GPX only where available.
2. RED/GREEN route-core tests: source segments, local bad point, duplicate/reversed
   times, gap/jump, measured-vs-interpolated flags, cell/time crossing, repeated
   traversal, uncertainty, pause union and exact 29m12s synthetic pause.
3. RED/GREEN capture tests: time-only positive, two individuals, other species and
   roadkill, captured/escaped identity, temporal boundary, overlapping sources,
   independent time+distance matching, repeated visits and strict no qualification.
4. RED/GREEN actual CLI integration: explicit input manifest, size/SHA tamper,
   malformed/deep/duplicate JSON/XML, private path confinement, changed source after
   processing, idempotence/conflicting output, no partial success and stdout privacy.
5. Execute authentic accessible measured GPX and source-bound capture inputs in
   private output storage. Independently audit outputs and reconcile all counts;
   report actual route recovery separately from scientific eligibility.
6. Review worker changes, update an additive coordinator record and immutable
   development cycle. Publish only reviewed code, synthetic tests and safe aggregate
   evidence to existing PR #136 within prior explicit owner authorization. Run and
   independently verify final exact-source-head Ubuntu CI.

## Completion boundaries

Deliver code and private source recovery where actual sources are accessible.
Missing private Library originals, independent label/search/outcome evidence,
untouched future evaluation, trusted issuer, real device acceptance and owner main/
production approval remain separate gates. Do not claim their success from
synthetic tests, private research receipts, GPX matches or retrospective fits.

## Executed follow-up (2026-11-04 JST)

- Repaired strict receipt types/source chronology, unknown capture uncertainty,
  simultaneous native brackets before road filtering, bounded map preflight and
  capacity fallback, local numeric overflow, and absent-road status.
- Added optional byte-bound route/qualified-fit diagnostics to the existing private
  handoff, retaining legacy model families and every scientific/production gate.
- Executed v4: 20 private jobs, 14 distinct GPX sources; preserve previous runs.
  Keep raw-statement30/source-view17/latest154 as unmerged event cohorts.
- Related regression suite:362=350PASS/12platformSKIP/0FAIL/0ERROR.
  Exact published-head Ubuntu CI remains a required separate evidence gate.
- Latest private inputs, independent scientific labels/as-of qualification, real
  prospective field E2E and owner main/production authority remain unavailable.
