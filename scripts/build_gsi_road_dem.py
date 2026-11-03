"""Convert official DEM10B PNG tiles to a source-bound 50 m road-neighbour grid.

Only the pinned public OSM archive drives network requests. No GPX/capture inputs
are accepted. Nearest source pixels preserve nodata; derivatives describe 50 m
spacing (100 m slope baseline), not measured road surface or verified shelter.
Outputs are append-only, outside Git. No model fit or forecast is performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from build_osm_prospective_universe import load_verified_road_csv, parse_road_cells, CELLS_SHA256
from gsi_dem_source_probe import tile, decode_rgb
from terrain_road_features import inverse_utm52n
from road_dem_join import join_road_dem

SPACING = 50
NODATA = -999999  # Outside the 24-bit GSI representable elevation range.
MAX_TILE_BYTES = 600000
MAX_BYTES = 150 * 1024 * 1024
MAX_TILES = 300
MAX_GRID_CELLS = 1200000
CODE_PATHS = ('scripts/build_gsi_road_dem.py', 'scripts/build_osm_prospective_universe.py',
              'scripts/gsi_dem_source_probe.py', 'src/terrain_road_features.py', 'src/road_dem_join.py')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def aware(value):
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError('Aware ISO timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('Aware ISO timestamp required')
    return result.astimezone(timezone.utc)


def private_root(path):
    path = Path(path)
    if '..' in path.parts:
        raise ValueError('Parent traversal forbidden')
    path = path.absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('Reparse paths forbidden')
        if (part / '.git').exists():
            raise ValueError('Output must be outside Git')
    return path


def child(root, relative):
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('Invalid relative source path')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or ':' in relative:
        raise ValueError('Source path escapes private root')
    return private_root(Path(root) / path)


def append_bytes(path, raw):
    path = private_root(path)
    if path.exists():
        if path.stat().st_size != len(raw):
            raise ValueError('Append-only collision')
        with path.open('rb') as stream:
            if stream.read(len(raw) + 1) != raw:
                raise ValueError('Append-only collision')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


class ByteBudget:
    def __init__(self, limit=MAX_BYTES):
        if type(limit) is not int or not 0 < limit <= MAX_BYTES:
            raise ValueError('Invalid aggregate byte limit')
        self.limit, self.used = limit, 0

    def consume(self, amount):
        if type(amount) is not int or amount < 0 or self.used + amount > self.limit:
            raise ValueError('Aggregate source byte budget exceeded')
        self.used += amount


def tile_url(identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'14-\d{1,5}-\d{1,5}', identifier):
        raise ValueError('Invalid fixed-layer tile identity')
    _, x, y = map(int, identifier.split('-'))
    if not 0 <= x < 16384 or not 0 <= y < 16384 or identifier != f'14-{x}-{y}':
        raise ValueError('Tile outside fixed zoom')
    return f'https://cyberjapandata.gsi.go.jp/xyz/dem_png/14/{x}/{y}.png'


def make_plan(cells):
    if not isinstance(cells, list) or not 0 < len(cells) <= 16990:
        raise ValueError('Invalid bounded road domain')
    seen, nodes = set(), set()
    for cell in cells:
        x, y = cell['x'], cell['y']
        if (type(x) not in (int, float) or type(y) not in (int, float)
                or not math.isfinite(x) or not math.isfinite(y)
                or not 100000 <= x < 900000 or not 0 <= y < 10000000
                or x % 100 != 50 or y % 100 != 50
                or cell['cell_id'] != f'utm52n_100m_{math.floor(x/100)}_{math.floor(y/100)}'
                or cell['cell_id'] in seen):
            raise ValueError('Road grid geometry mismatch')
        seen.add(cell['cell_id'])
        nodes.update((x + dx * SPACING, y + dy * SPACING)
                     for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    xmin, xmax = min(p[0] for p in nodes), max(p[0] for p in nodes)
    ymin, ymax = min(p[1] for p in nodes), max(p[1] for p in nodes)
    nc, nr = int((xmax-xmin)/SPACING)+1, int((ymax-ymin)/SPACING)+1
    if nc * nr > MAX_GRID_CELLS:
        raise ValueError('Raster extent exceeds bound')
    entries = []
    for x, y in nodes:
        lat, lon = inverse_utm52n(x, y)
        tx, ty, px, py = tile(lat, lon, 14)
        entries.append(dict(row=int((ymax-y)/SPACING), col=int((x-xmin)/SPACING),
                            x=x, y=y, tile_id=f'14-{tx}-{ty}', pixel_x=px, pixel_y=py))
    entries.sort(key=lambda n: (n['row'], n['col']))
    identifiers = sorted({n['tile_id'] for n in entries})
    if len(identifiers) > MAX_TILES:
        raise ValueError('Tile domain exceeds bound')
    return dict(ncols=nc, nrows=nr, x0=xmin-SPACING/2, y0=ymin-SPACING/2,
                cellsize=SPACING, nodes=entries, tiles=identifiers)


def open_dem_png(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_TILE_BYTES:
        raise ValueError('Invalid bounded PNG body')
    try:
        with Image.open(io.BytesIO(raw)) as picture:
            if picture.format != 'PNG' or picture.size != (256, 256) or picture.mode != 'RGB':
                raise ValueError('Expected 256x256 24-bit RGB DEM PNG')
            picture.load()
            return picture.copy()
    except (OSError, ValueError) as error:
        raise ValueError('Invalid DEM PNG') from error


def _download(url):
    try:
        with urlopen(Request(url, headers={'User-Agent': 'HabuAI public-road DEM provenance research'}), timeout=20) as response:
            return response.status, response.url, response.read(MAX_TILE_BYTES + 1)
    except HTTPError as error:
        return error.code, error.url, error.read(MAX_TILE_BYTES + 1)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def read_receipt(path):
    with private_root(path).open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('Receipt byte bound exceeded')
    return json.loads(raw, object_pairs_hook=_unique_object)


def validate_source(root, identifier, receipt, budget):
    expected_url = tile_url(identifier)
    if (receipt.get('schema_version') != 'gsi-dem-tile-receipt-v1'
            or receipt.get('tile_id') != identifier or receipt.get('provider') != 'GSI'
            or receipt.get('layer') != 'dem_png' or receipt.get('http_status') != 200
            or receipt.get('content_status') != 'VALID_RGB_DEM'
            or receipt.get('requested_url') != expected_url or receipt.get('resolved_url') != expected_url):
        raise ValueError('Tile receipt source mismatch')
    retrieved, received = aware(receipt.get('retrieved_at')), aware(receipt.get('source_received_at'))
    if received < retrieved:
        raise ValueError('Receipt chronology mismatch')
    size, sha = receipt.get('size_bytes'), receipt.get('sha256')
    if type(size) is not int or not 0 < size <= MAX_TILE_BYTES or not isinstance(sha, str) or not re.fullmatch(r'[a-f0-9]{64}', sha):
        raise ValueError('Invalid source size or digest')
    expected_file = f'incoming/{identifier}-{sha}.source'
    if receipt.get('raw_file') != expected_file:
        raise ValueError('Unexpected raw source path')
    with child(root, expected_file).open('rb') as stream:
        raw = stream.read(MAX_TILE_BYTES + 1)
    budget.consume(len(raw))
    if len(raw) != size or digest(raw) != sha:
        raise ValueError('Retained source byte integrity mismatch')
    open_dem_png(raw)
    return dict(raw=raw, receipt=dict(receipt))


def acquire_tile(root, identifier, *, budget, fetch=None, clock=None, pause=None):
    root = private_root(root)
    url = tile_url(identifier)
    receipt_path = child(root, f'receipts/{identifier}.json')
    if receipt_path.exists():
        return validate_source(root, identifier, read_receipt(receipt_path), budget)
    fetch, clock = fetch or _download, clock or (lambda: datetime.now(timezone.utc))
    pause = pause or (lambda: time.sleep(1))
    for attempt in (1, 2):
        pause()  # Every network attempt, including retry, is paced.
        try:
            status, resolved, raw = fetch(url)
        except (URLError, OSError) as error:
            now = clock().isoformat(); aware(now)
            failure = dict(tile_id=identifier, requested_url=url, attempt=attempt,
                           actual_time=now, error=type(error).__name__, status='TRANSPORT_FAILURE')
            append_bytes(child(root, f'attempts/{identifier}-{digest(encoded(failure))}.json'), encoded(failure))
            continue
        if not isinstance(raw, bytes):
            raise ValueError('Source body must be bytes')
        budget.consume(len(raw))
        if len(raw) > MAX_TILE_BYTES:
            raise ValueError('Per-request byte bound exceeded')
        now = clock().isoformat(); aware(now)
        sha = digest(raw)
        relative = f'incoming/{identifier}-{sha}.source'
        append_bytes(child(root, relative), raw)
        valid = False
        if status == 200 and resolved == url:
            try:
                open_dem_png(raw)
                valid = True
            except ValueError:
                pass
        receipt = dict(schema_version='gsi-dem-tile-receipt-v1', provider='GSI',
            tile_id=identifier, layer='dem_png', requested_url=url, resolved_url=resolved,
            http_status=status, retrieved_at=now, source_received_at=now,
            size_bytes=len(raw), sha256=sha, raw_file=relative,
            content_status='VALID_RGB_DEM' if valid else 'UNUSABLE_RESPONSE',
            historical_publication_time='NOT_ESTABLISHED',
            licence_url='https://maps.gsi.go.jp/development/ichiran.html')
        append_bytes(child(root, f'attempts/{identifier}-{digest(encoded(receipt))}.json'), encoded(receipt))
        if valid:
            append_bytes(receipt_path, encoded(receipt))
            return dict(raw=raw, receipt=receipt)
        if status == 404:
            break
    return None


def sample_plan(plan, sources):
    pictures = {}
    for identifier, source in sources.items():
        if digest(source['raw']) != source['receipt']['sha256']:
            raise ValueError('Source changed before pixel sampling')
        pictures[identifier] = open_dem_png(source['raw'])
    values, mapping = {}, []
    for node in plan['nodes']:
        ident = node['tile_id']
        value, status, sha = None, 'UNKNOWN_TILE_UNAVAILABLE', None
        if ident in pictures:
            value = decode_rgb(pictures[ident].getpixel((node['pixel_x'], node['pixel_y'])))
            status = 'SOURCE_PIXEL_SAMPLED' if value is not None else 'UNKNOWN_SOURCE_NODATA'
            sha = sources[ident]['receipt']['sha256']
        values[node['row'], node['col']] = NODATA if value is None else value
        mapping.append(dict(node, value_m=value, status=status, source_sha256=sha))
    return values, mapping


def ascii_bytes(plan, values):
    header = (f"ncols {plan['ncols']}\nnrows {plan['nrows']}\nxllcorner {plan['x0']}\n"
              f"yllcorner {plan['y0']}\ncellsize {SPACING}\nNODATA_value {NODATA}\n")
    lines = [' '.join(f'{values.get((r, c), NODATA):.2f}' for c in range(plan['ncols']))
             for r in range(plan['nrows'])]
    return (header + '\n'.join(lines) + '\n').encode('ascii')


def write_derived(root, relative, raw, *, source_ready, code_sha256):
    derived = datetime.now(timezone.utc)
    path = child(root, relative)
    append_bytes(path, raw)
    materialized = datetime.now(timezone.utc)
    with private_root(path).open('rb') as stream:
        if stream.read(len(raw) + 1) != raw:
            raise ValueError('Derived readback mismatch')
    audited = datetime.now(timezone.utc)
    if aware(source_ready) > derived:
        raise ValueError('Future source receipt')
    receipt = dict(schema_version='gsi-derived-readiness-v1', path=relative,
        sha256=digest(raw), size_bytes=len(raw), source_received_at=source_ready,
        derived_at=derived.isoformat(), materialized_at=materialized.isoformat(),
        audited_at=audited.isoformat(), usable_at=max(aware(source_ready), derived, materialized, audited).isoformat(),
        code_sha256=code_sha256)
    sealed = encoded(receipt)
    seal_path = relative + '.' + digest(sealed) + '.readiness.json'
    append_bytes(child(root, seal_path), sealed)
    return dict(receipt, readiness_receipt=dict(path=seal_path, sha256=digest(sealed), size_bytes=len(sealed)))


def validate_derived(root, artifact, budget):
    """Recheck actual artifact and exact sealed readiness bytes before completion."""
    seal = artifact.get('readiness_receipt')
    if not isinstance(seal, dict):
        raise ValueError('Missing readiness receipt binding')
    for ref, limit in ((artifact, 64 * 1024 * 1024), (seal, 65536)):
        size = ref.get('size_bytes')
        if type(size) is not int or not 0 < size <= limit:
            raise ValueError('Derived reference byte bound invalid')
        path = child(root, ref['path'])
        if path.stat().st_size != size:
            raise ValueError('Derived artifact or readiness size changed')
        with path.open('rb') as stream:
            raw = stream.read(size + 1)
        budget.consume(len(raw))
        if len(raw) != size or digest(raw) != ref.get('sha256'):
            raise ValueError('Derived artifact or readiness digest changed')
        if ref is seal:
            body = {key: value for key, value in artifact.items() if key != 'readiness_receipt'}
            if raw != encoded(body):
                raise ValueError('Readiness receipt does not match artifact reference')
    stamps = [aware(artifact[key]) for key in
              ('source_received_at', 'derived_at', 'materialized_at', 'audited_at')]
    if stamps != sorted(stamps) or aware(artifact['usable_at']) != max(stamps):
        raise ValueError('Derived readiness chronology mismatch')


def processing_cutoff(ready, *, clock=None, pause=None):
    clock = clock or (lambda: datetime.now(timezone.utc))
    pause = pause or (lambda: time.sleep(0.002))
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        now = clock().isoformat()
        if aware(now) > aware(ready):
            return now
        pause()
    raise ValueError('Actual processing clock has not advanced beyond readiness')


def build(output_root):
    output_root = private_root(output_root)
    # No user-supplied road CSV or coordinates: only the pinned public archive.
    road_raw = load_verified_road_csv(ROOT)
    if digest(road_raw) != CELLS_SHA256:
        raise ValueError('Pinned public road hash mismatch')
    road_read_at = datetime.now(timezone.utc).isoformat()
    plan = make_plan(parse_road_cells(road_raw))
    code = {path: digest((ROOT / path).read_bytes()) for path in CODE_PATHS}
    generation = 'derived/' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    budget, sources, failures = ByteBudget(), {}, []
    for index, identifier in enumerate(plan['tiles'], 1):
        source = acquire_tile(output_root, identifier, budget=budget)
        if source is None:
            failures.append(identifier)
        else:
            sources[identifier] = source
        print(json.dumps(dict(tile=index, total=len(plan['tiles']), source_bytes=budget.used,
                              missing_tiles=len(failures))), flush=True)
    source_ready = max([aware(road_read_at)] + [aware(s['receipt']['source_received_at']) for s in sources.values()]).isoformat()
    road = write_derived(output_root, generation + '/verified-public-roads.csv', road_raw,
                         source_ready=road_read_at, code_sha256=code)
    values, mapping = sample_plan(plan, sources)
    dem = write_derived(output_root, generation + '/road-neighbour-dem-50m.asc', ascii_bytes(plan, values),
                        source_ready=source_ready, code_sha256=code)
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(mapping[0]))
    writer.writeheader(); writer.writerows(mapping)
    mapped = write_derived(output_root, generation + '/required-node-source-map.csv', stream.getvalue().encode('utf-8'),
                           source_ready=source_ready, code_sha256=code)
    # This is the actual post-materialization processing time, never a past P0 cutoff.
    cutoff = processing_cutoff(max(road['usable_at'], dem['usable_at'], key=aware))
    joined = join_road_dem(child(output_root, road['path']), child(output_root, dem['path']),
        road_sha256=road['sha256'], dem_sha256=dem['sha256'], dem_epsg=32652,
        road_available_at=road['usable_at'], dem_available_at=dem['usable_at'], cutoff_time=cutoff)
    joined.update(derivative_grid_spacing_m=50, slope_difference_baseline_m=100,
        tpi_support='3x3 target nodes at 50m spacing', resampling='NEAREST_GSI_PIXEL_CENTRE',
        source_vertical_datum='GSI_PUBLISHED_HEIGHT_UNCONVERTED',
        terrain_wind_shielding_verified=False, historical_ex_ante_proven=False,
        training_eligibility='NOT_ASSESSED')
    join = write_derived(output_root, generation + '/road-dem-join.json', encoded(joined),
                         source_ready=max((road['usable_at'], dem['usable_at'], mapped['usable_at']), key=aware), code_sha256=code)
    # Recheck retained sources and code after the actual join.
    verify_budget = ByteBudget()
    source_refs = []
    for identifier, source in sources.items():
        receipt_relative = f'receipts/{identifier}.json'
        current = read_receipt(child(output_root, receipt_relative))
        if current != source['receipt']:
            raise ValueError('Source receipt changed during derivation')
        validate_source(output_root, identifier, current, verify_budget)
        source_refs.append(dict(tile_id=identifier, path=receipt_relative,
            receipt_sha256=digest(child(output_root, receipt_relative).read_bytes()),
            raw_sha256=current['sha256'], source_received_at=current['source_received_at']))
    if load_verified_road_csv(ROOT) != road_raw or any(digest((ROOT / p).read_bytes()) != h for p, h in code.items()):
        raise ValueError('Code or public road source changed during build')
    report = dict(schema_version='gsi-road-dem-conversion-v1',
        status=joined['status'], grid={k: v for k, v in plan.items() if k not in ('nodes', 'tiles')},
        tile_count=len(plan['tiles']), received_tiles=len(sources), unavailable_tiles=failures,
        source_bytes=budget.used, required_nodes=len(mapping), node_status_counts=dict(Counter(n['status'] for n in mapping)),
        total_cells=joined['total_cells'], coverage_cells=joined['coverage_cells'], missing_cells=joined['missing_cells'],
        road_sha256=CELLS_SHA256, code_sha256=code, artifacts=[road, dem, mapped, join],
        source_receipts=source_refs,
        source_projection='GSI slippy pixels; existing WGS84 inverse UTM52N; nearest pixel centre',
        target_crs='EPSG:32652', unrequested_grid_nodes='NODATA_NOT_REQUESTED',
        terrain_wind_shielding_verified=False, formal_p0_eligible=False,
        historical_ex_ante_proven=False, training_eligibility='NOT_ASSESSED',
        completed_at=datetime.now(timezone.utc).isoformat())
    derived_budget = ByteBudget()
    for artifact in report['artifacts']:
        validate_derived(output_root, artifact, derived_budget)
    report['final_derived_readback_bytes'] = derived_budget.used
    filename = 'conversion-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'
    append_bytes(child(output_root, filename), encoded(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', required=True, type=Path)
    args = parser.parse_args()
    result = build(args.output_root)
    print(json.dumps({k: result[k] for k in ('status', 'total_cells', 'coverage_cells', 'missing_cells', 'source_bytes')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
