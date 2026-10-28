# Read-only P0 preflight implementation plan

> Agent execution: use the existing architecture and test-first implementation;
> the owner explicitly requested autonomous execution without routine approvals.

Goal: return the real fail-closed P0 readiness JSON on Windows without importing
the execution-only POSIX Champion registry.

Architecture: extract the two existing authority-policy metadata constants into
a pure shared module. The registry and checker import the same unchanged
constants. Execution locks, sandbox identity and production gates stay intact.
Python standard library only; no new dependencies, privileges or services.

Spec: AGENTS.md, Issue64, CODEX_ACCEPTANCE_20261025.md, and the existing
check_p0_readiness.inspect contract. This implements diagnostic portability,
not production authority or formal P0 issuance.

## Task1: isolate metadata and retain fail-closed inspection

- [ ] Add a real subprocess CLI regression with fcntl unavailable. It must
  return exit2, parseable BLOCKED JSON, unchanged production blockers and no
  filesystem writes. Run it before implementation and retain the failing log.
- [ ] Add src/prediction_authority_policy.py with unchanged SCOPE and
  AUTHORITY_BLOCKER; import from both checker and registry. No new authority API.
- [ ] Execute the canonical observer preflight on all supported platforms;
  update the Windows regression to require real checker output.
- [ ] Run readiness/observer and registry tests; retain Windows capability
  errors separately from genuine Ubuntu CI, without shimming production locks.
- [ ] Independent review; native-LF code closure freeze and append-only state
  update; exact-head full CI; approved code-only merge; fresh-main CI.

## Review focus

Missing or historical start must still block; existing P0 bytes must be
unchanged; metadata cannot grant activation; absent POSIX locks must still
prevent registry execution; fixtures never prove prospective field E2E.

## Master dependency order

First repair existing PR151's historical-v4 test fixture and obtain its own
CI/review. Keep PR147 source intake unmerged. Integrate this separate diagnostic
slice only against freshly accepted main. Scientific search/outcome eligibility,
full ex-ante road/features, real fitting/confirmation, formal targets/routes,
trusted production activation and the actual next search remain separate gates.
