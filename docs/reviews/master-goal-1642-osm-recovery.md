# OSM archive recovery audit

The OSM payloads are present in the pinned repository archive. Earlier local-file absence was an incomplete materialization, not repository absence. This report supersedes the missing-OSM-bytes finding in evidence-audit-followon-design.md. Historical prediction access remains unverified.

## Provenance and verified recovery

- Repository: haji84/habuAI-private; pinned commit c1acabe1e2e6f6959c0a949bd18c37f174480c5a.
- Source directory: artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts/.
- Retrieved README.md and part_000.b64 through part_032.b64 using the existing GitHub file capability at that commit. No external OSM request, credential fallback, or bundled-code execution.
- Each of the **34 source blobs** passed exact size and Git blob SHA-1 against main-tree.json: SHA1(`blob <byte-length>\0` + bytes). Parts total 6,460,688 base64 bytes. A short local write of part023 was caught by this check, rewritten from the same fetched content, and all checks rerun successfully.
- Strict base64 decoding produced a 4,845,515-byte ZIP. SHA-256 matches the source README: **f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17**.
- ZIP CRC check passed for all members. Before extraction, checked member count <10,000, cumulative declared uncompressed size <300MB, each member <100MB, no absolute/traversal/Windows-drive/backslash paths, duplicate members, symlinks or encryption. Extraction used bounded declared members, and checked actual byte sizes afterward.
- Extracted **112 files**, 28,325,900 uncompressed bytes; every file has SHA-256 and size in osm-recovery/inventory.json. All writes remained under osm-recovery plus this report. No repository/raw/ORIGINAL/code was changed.

## Manifest results and usable data

Both the repository evidence/osm/osm_road_evidence_manifest.csv and extracted 12_evidence/osm_road_evidence_manifest.csv have **99 rows**. All 99 rows resolve by exact SHA-256 **and size** to extracted bytes; both manifest files are the same content hash. This is separate from the 112 total extracted files, which are all inventoried and hashed.

| Logical extracted path | Bytes | SHA-256 |
|---|---:|---|
| 02_raw_road/osm_island_boundaries.geojson | 931714 | ab709f5110d342eba27aaae153685bc4e1dab325adf6fe19d91bb2ca45aba225 |
| 04_processed_road/osm_road_candidate_cells.csv | 4408826 | 33ea1df38351d9c2454bf2efc9b00432119e484d5d549a567bc8fd2d337151a4 |
| 04_processed_road/osm_road_candidate_cells.parquet | 1032104 | 0e23ac2e07afdf3f9734a46db4171ac7f5a46a2bd8cadc2e706b86fe98b72ac9 |
| 04_processed_road/osm_road_centerlines.geojsonl | 5553926 | e5bfff98fc1af8d118d18f46b6d289a0db7f8b69cd4807fb0966103a0f57348e |
| 04_processed_road/osm_processing_audit.json | 1503 | 7c37747247e7f276b4280f6a9c17ef6e9683cfae4daaa3702b71a5fd8de907c6 |

The old absolute manifest prefix `/workspace/scratch/e1ebfc520ed2/habu_project/` maps to `/workspace/scratch/fb45a4f31791/osm-recovery/extracted/`. Mapping was accepted only after SHA+size match; it was not a blind filesystem redirection. inventory.json records every declared old path and matched extracted relative path.

Actual CSV inspection: 16,990 rows, 16,990 unique cell IDs and index pairs; 15,329 Amami-main /1,661 Kakeroma cells; no out-of-range latitude/longitude or negative road lengths. There are 6,583 centerline JSONL rows and 2 island-boundary features. This was schema/count/hash inspection, not rerunning the geospatial pipeline or validating road access in the field. Parquet bytes were verified, not independently decoded/cross-compared with CSV.

Cells include UTM52N 100m indices and exact center coordinates, road_length_m, density, segment_count, OSM IDs, island ID, highway/group/surface values, missingness, bridge/tunnel and direction fields. source/candidate_source declare **OpenStreetMap auxiliary / osm_auxiliary**. Preserve this class; it cannot satisfy an official-road-only policy by relabeling.

## Acquisition groups and timing limitations

The acquisition CSV contains 109 records: 1 cached boundary, **20 used cached road tiles**, 16 outside-target skipped tiles (no payload/hash), and **72 retained-not-used raw tiles**. All **93 hashed acquisition records** (boundary+92 tile JSONs) resolve to extracted bytes. inventory.json.acquisition_groups records these groups separately; do not treat retained superseded files as additional selected model inputs.

- Twenty used tiles and the boundary have September25 `retrieved_at_utc` metadata and `cached` status. Read-only inspection of bundled scripts/fetch_osm_road.py shows cached rows are stamped with datetime.now when cache is read. These timestamps establish the semantics of the archived process claim, not independently verified first download or model access.
- Seventy-two retained tiles explicitly carry `retrieval_time_status=filesystem_mtime_recovered` and `attempts=unknown_recovered`. These are not reliable historical access receipts.
- `osm_base_timestamp` is the provider data snapshot watermark, not prediction-process availability. ZIP timestamps have no reliable timezone/access chain. Archive filename, report creation date and pinned repository presence likewise do not establish when a historical prediction consumed these files.
- Processing audit claims created_at_utc 2026-09-25T01:58:07.171351+00:00. It is useful source metadata, not a pre-reveal model/universe freeze. No genuine historical prediction input-lineage proof was found in this bundle.

Recovered data remove the **missing bytes** blocker for prospective auxiliary roads/domain/grid inputs. An actual audit now may record verified materialization availability (timestamp included in inventory.json), then a permitted future model may freeze these hashes and generate its declared future cell/time universe. This archive alone is a spatial grid: no requested forecast window, cutoff, per-time-row freeze, current search role, capture outcome completeness or independent confirmation evidence is supplied.

The bundled top-level README describes many broader datasets/model results not included in this OSM-only ZIP (weather, exposure, historic frozen predictions, reports). Those textual claims must not be treated as recovered payloads. The 112-member inventory is the actual recovery scope.

## Reproduction without executing bundled scripts

The machine inventory schema is `osm-recovery-inventory-v1`: pinned_commit, parts[{path,size,expected_size,git_blob_sha,expected_git_blob_sha,verified}], archive{size_bytes,sha256,zip_crc_all_pass}, limits, files[{path,size_bytes,sha256,zip_mtime}], manifest_comparisons, acquisition_summary, acquisition_groups, dataset_summary and availability_assessment. Paths are relative to the extracted directory; inventory itself is outside the repository.

To independently reproduce the key integrity assertions from recovered parts (read-only, no bundled code):

```bash
python - <<'PY'
from pathlib import Path
import base64, hashlib, io, json, zipfile
b=Path('/workspace/scratch/fb45a4f31791')
r=b/'osm-recovery'
t=json.loads((b/'main-tree.json').read_text())
for x in t['tree']:
    if x['type']=='blob' and x['path'].startswith('artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts/'):
        raw=(r/'parts'/Path(x['path']).name).read_bytes()
        assert len(raw)==x['size']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==x['sha']
raw=base64.b64decode(b''.join(p.read_bytes() for p in sorted((r/'parts').glob('part_*.b64'))),validate=True)
assert hashlib.sha256(raw).hexdigest()=='f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17'
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None
i=json.loads((r/'inventory.json').read_text())
for x in i['files']:
    raw=(r/'extracted'/x['path']).read_bytes()
    assert len(raw)==x['size_bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256']
assert all(row['status']=='PASS' for m in i['manifest_comparisons'] for row in m['rows'])
print('All source blobs, archive CRC/SHA, extracted bytes and recorded manifest comparisons pass')
PY
```

No model/scientific/road-map-match tests or historical access verification are claimed by this integrity reproduction.
