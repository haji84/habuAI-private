# Source-freeze path ancestry boundary

The master snapshot guard was merged in PR #97. The separate source-freeze
checker still used its older local path guard, which checked the lexical root
and descendants but omitted ancestors above the root.

A native Windows reproduction placed a real junction above the fixture root.
The previous `code_paths` enumerated the external src/scripts/schemas targets
six times and accepted the ancestry. This is the reproduced defect. The
existing nested-junction controls already rejected before external enumeration;
the earlier generic concern about `rglob` is not evidence that those controls
were bypassed.

The checker now reuses the reviewed master guard for roots, all ancestors and
reference components, and the same iterative guarded source walker. Source
selection, source byte hashing, policy, limits, old freezes and authorization
remain unchanged. These checks cover static links and ordinary changes, not
hostile concurrent filesystem replacement.

TDD: four new controls initially had one failure (the root-ancestor case). After
repair all four pass with zero external scans. The existing cycle/readiness/
cursor tests and master boundary controls total 51 tests: 47 pass and four
Linux-only controls are explicitly skipped on native Windows. Real Windows
junction fixtures are removed as links only, within their verified temporary
workspace; the external sentinel remains unchanged. Linux uses real symlinks.

Commands:

```text
python -X utf8 -m unittest discover -s tests -p 'test_codex_cycle*.py' -q
python -X utf8 -m unittest discover -s tests -p test_master_inventory.py -q
```

A new source freeze and exact-head Ubuntu full CI are required before merge.
No field data, model fits, accuracy metrics or production authority are added.
