"""Synthetic strict G0 contracts: software consistency, never scientific evidence."""
import copy
import hashlib
import importlib
import base64
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from master_contracts import canonical_bytes, digest
from models.research_selection import validate_future_rows
import prospective_inputs as pi

NIGHT = '2026-10-14'
CUTOFF = NIGHT + 'T18:00:00+09:00'
READY = NIGHT + 'T17:00:00+09:00'
NOW = datetime.fromisoformat(NIGHT + 'T18:30:00+09:00')
START = NIGHT + 'T19:00:00+09:00'
END = NIGHT + 'T19:20:00+09:00'
POLICY = 'protocols/development/g0-policy-v1.json'


def base_ref(root, path, raw):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return dict(path=path, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def readiness():
    return {name: READY for name in pi.READINESS_FIELDS}


def bound(ref):
    return dict(ref, readiness=readiness(), usable_at=READY)


def row_id(cell, when):
    stamp = when.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return f'{cell[0]}:{cell[1]}@{stamp}'


def definition_hash(features):
    identities = []
    for feature in features:
        item = copy.deepcopy(feature)
        item['code_ref'] = {key: item['code_ref'][key] for key in ('path', 'sha256', 'size_bytes')}
        identities.append(item)
    return digest(sorted(identities, key=lambda item: item['name']))


class SyntheticContract:
    def __init__(self, root):
        self.root = root
        self.objects = {}
        self.nodes = {}
        self.snapshots = []
        self.cells = [[4000, 30000], [4001, 30000]]
        self.valid = dict(start=START, end=END)
        self.policy = bound(base_ref(root, POLICY, (ROOT / POLICY).read_bytes()))
        code = bound(base_ref(root, 'src/synthetic_feature.py', b'# synthetic fixture only\n'))
        self.features = [dict(name='rain_3h_mm', units='mm', version='1',
                              definition='Forecast precipitation for the declared window',
                              definition_sha256=hashlib.sha256(b'Forecast precipitation for the declared window').hexdigest(),
                              code_ref=code, deployment='forecast_predictor',
                              required_source_ids=['weather'])]
        self.add('roads', 'features/sources/roads.json', 'static', 'universe', [],
                 dict(schema_version='habu-g0-source-v1', source_kind='static', source_class='official',
                      event_time=NIGHT + 'T16:00:00+09:00', valid_time=self.valid, data={'road_cells': self.cells}))
        self.add('weather', 'features/sources/weather.json', 'forecast', 'feature', [],
                 dict(schema_version='habu-g0-source-v1', source_kind='forecast', source_class='official',
                      event_time=NIGHT + 'T16:00:00+09:00', valid_time=self.valid, data={'synthetic_only': [0.5]}))
        self.add('domain', 'features/domain.json', 'cell_domain', 'universe', ['roads'],
                 dict(schema_version='habu-g0-cell-domain-v1', crs='EPSG:32652',
                      source_class='official', required_source_ids=['roads'], cells=self.cells))
        shards = []
        for ci, cell in enumerate(self.cells):
            for ti in range(2):
                sid = f'c{ci}t{ti}'
                window = datetime.fromisoformat(START) + timedelta(minutes=10 * ti)
                rid = row_id(cell, window)
                universe = dict(schema_version='1.0', source_type='EX_ANTE_FORECAST',
                                geographic_domain={'crs': 'EPSG:32652', 'name': 'synthetic'}, rows=[
                                    dict(row_id=rid, operational_night=NIGHT, cutoff_time=CUTOFF,
                                         window_start_jst=window.isoformat(),
                                         utm_x_m=cell[0] * 100 + 50, utm_y_m=cell[1] * 100 + 50)])
                self.add(sid + '-u', f'features/{sid}-universe.json', 'forecast_universe', 'universe', ['domain'], universe)
                feature = dict(schema_version='1.0', operational_night=NIGHT, cutoff_time=CUTOFF,
                               available_at=READY, feature_name='rain_3h_mm', use_role='forecast_predictor',
                               values={rid: 0.5 + ci + ti})
                self.add(sid + '-f', f'features/{sid}-feature.json', 'feature_values', 'feature', ['weather'], feature)
                snapshot = dict(schema_version='2.0', operational_night=NIGHT, cutoff_time=CUTOFF,
                                universe={'path': self.nodes[sid + '-u']['ref']['path']},
                                features=[{'path': self.nodes[sid + '-f']['ref']['path']}],
                                feature_schema_sha256=digest(['rain_3h_mm']))
                self.add(sid + '-s', f'features/{sid}-snapshot.json', 'snapshot', 'protocol', [sid + '-u', sid + '-f'], snapshot)
                self.snapshots.append(sid + '-s')
                validity = dict(schema_version='habu-g0-validity-v1', feature_sources={'rain_3h_mm': [sid + '-f']},
                                rows={rid: {'rain_3h_mm': self.valid.copy()}})
                self.add(sid + '-v', f'features/{sid}-validity.json', 'validity', 'protocol', [sid + '-f'], validity)
                shards.append(dict(shard_id=sid, cell_partition=ci, time_partition=ti,
                                   snapshot_id=sid + '-s', validity_id=sid + '-v'))
        self.manifest = dict(schema_version='habu-g0-forecast-contract-v1', operational_night=NIGHT,
                             cutoff_time=CUTOFF, readiness=readiness(), usable_at=READY,
                             policy_ref=self.policy, domain_id='domain', source_nodes=list(self.nodes.values()),
                             features=self.features, feature_definition_sha256=definition_hash(self.features),
                             horizon=self.valid.copy(), cell_partitions=[[0, 1], [1, 2]],
                             time_partitions=[[0, 1], [1, 2]], shards=shards)
        self.publish()

    def add(self, identifier, path, kind, role, parents, value):
        self.objects[path] = value
        self.nodes[identifier] = dict(id=identifier, ref={'path': path}, source_kind=kind, role=role,
                                      allowed_use='FORECAST_INPUT', parents=parents, readiness=readiness(),
                                      usable_at=READY, event_time=(value.get('event_time') if kind in ('static', 'forecast') else None),
                                      valid_time=self.valid.copy(), source_class='official')

    def publish(self):
        for identifier, node in self.nodes.items():
            if identifier in self.snapshots:
                continue
            path = node['ref']['path']
            node['ref'] = base_ref(self.root, path, canonical_bytes(self.objects[path]) + b'\n')
        for identifier in self.snapshots:
            node = self.nodes[identifier]
            snap = self.objects[node['ref']['path']]
            for ref in [snap['universe'], *snap['features']]:
                ref.update(next(dict(n['ref'], available_at=READY) for n in self.nodes.values() if n['ref']['path'] == ref['path']))
            path = node['ref']['path']
            node['ref'] = base_ref(self.root, path, canonical_bytes(snap) + b'\n')
        self.manifest['source_nodes'] = list(self.nodes.values())
        self.ref = base_ref(self.root, 'features/g0-contract.json', canonical_bytes(self.manifest) + b'\n')

    def manifest_only(self):
        self.manifest['source_nodes'] = list(self.nodes.values())
        self.ref = base_ref(self.root, 'features/g0-contract.json', canonical_bytes(self.manifest) + b'\n')

    def overwrite_node_raw(self, identifier, raw):
        node = self.nodes[identifier]
        node['ref'] = base_ref(self.root, node['ref']['path'], raw)
        self.manifest_only()


class G0ForecastTests(unittest.TestCase):
    def setUp(self):
        try:
            self.g0 = importlib.import_module('g0_forecast_contract')
        except ModuleNotFoundError:
            self.fail('Additive strict G0 forecast API is missing')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = SyntheticContract(self.root)

    def call(self, load=False, **kwargs):
        function = self.g0.load_g0_forecast_rows if load else self.g0.validate_g0_forecast
        return function(self.root, self.fixture.ref, NIGHT, NOW,
                        expected_feature_definition_sha256=definition_hash(self.fixture.features), **kwargs)

    def test_complete_rectangles_return_distinct_hashes_and_no_authority(self):
        result = self.call(load=True)
        receipt = result['receipt']
        self.assertEqual(len(result['rows']), 4)
        self.assertEqual(receipt['row_count'], 4)
        self.assertEqual(receipt['feature_definition_sha256'], definition_hash(self.fixture.features))
        self.assertEqual(receipt['legacy_feature_names_sha256'], digest(['rain_3h_mm']))
        self.assertNotEqual(receipt['feature_definition_sha256'], receipt['legacy_feature_names_sha256'])
        self.assertEqual(receipt['policy_file_sha256'], self.fixture.policy['sha256'])
        self.assertFalse(receipt['fit_authorized'])
        self.assertFalse(receipt['scientific_execution_authorized'])
        self.assertFalse(receipt['production_authorized'])
        self.assertEqual(receipt['source_authenticity'], 'NOT_ATTESTED')

    def test_model_boundary_keeps_exact_returned_row_digest_and_normalized_shape(self):
        result = self.call(load=True)
        receipt, rows = result['receipt'], result['rows']
        self.assertEqual(receipt['canonical_joined_rows_sha256'], digest(rows))
        checked = validate_future_rows(rows, cutoff_time=CUTOFF, universe_sha256=digest(rows),
                                       heldout_night=NIGHT, feature_names=['rain_3h_mm'])
        self.assertEqual(checked, rows)
        self.assertEqual(digest(checked), receipt['canonical_joined_rows_sha256'])
        self.assertEqual(rows[0]['cell_x'], 4000)
        self.assertEqual(rows[0]['cell_y'], 30000)
        self.assertTrue(rows[0]['window_start_jst'].endswith('+00:00'))
        self.assertEqual(receipt['snapshot_refs'], [self.fixture.nodes[x]['ref'] for x in self.fixture.snapshots])

    def test_receipt_only_hash_matches_complete_collector(self):
        receipt = self.call()
        complete = self.call(load=True)
        self.assertEqual(receipt['canonical_joined_rows_sha256'], digest(complete['rows']))

    def test_pure_readiness_graph_returns_parent_first_order_without_forecast_roles(self):
        projection = [{key: node[key] for key in ('id', 'parents', 'readiness', 'usable_at')}
                      for node in reversed(list(self.fixture.nodes.values()))]
        calls = [0]
        def check():
            calls[0] += 1
        result = self.g0.validate_readiness_graph(projection, datetime.fromisoformat(CUTOFF), check=check)
        order = result['topological_order']
        for node in projection:
            for parent in node['parents']:
                self.assertLess(order.index(parent), order.index(node['id']))
        self.assertEqual(set(result['ready_by_id']), set(self.fixture.nodes))
        self.assertGreater(calls[0], len(projection))

    def test_pure_readiness_graph_rejects_cycles_missing_parents_and_unknown_fields(self):
        root = dict(id='root', parents=[], readiness=readiness(), usable_at=READY)
        for changed in [dict(root, parents=['root']), dict(root, parents=['absent']), dict(root, role='label')]:
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    self.g0.validate_readiness_graph([changed], datetime.fromisoformat(CUTOFF))

    def test_pure_readiness_graph_checks_longest_path_even_when_parents_cached(self):
        nodes = [dict(id=f'n{x}', parents=[f'n{x - 1}'] if x else [], readiness=readiness(), usable_at=READY)
                 for x in range(4)]
        with patch.object(self.g0, 'MAX_SOURCE_DEPTH', 3):
            with self.assertRaises(self.g0.ForecastCapacityError):
                self.g0.validate_readiness_graph(nodes, datetime.fromisoformat(CUTOFF))

    def test_strict_root_ancestor_indirection_rejects_before_any_byte_open(self):
        with tempfile.TemporaryDirectory() as folder:
            container = Path(folder).resolve()
            external, alias = container / 'external', container / 'alias'
            fixture = SyntheticContract(external / 'workspace')
            sentinel = external / 'preserve-sentinel.txt'
            sentinel.write_bytes(b'external evidence preserved')
            if os.name == 'nt':
                result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(external)],
                                        capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
            else:
                alias.symlink_to(external, target_is_directory=True)
            opened = []
            original = Path.open
            def count_open(path, *args, **kwargs):
                opened.append(str(path))
                return original(path, *args, **kwargs)
            try:
                with patch.object(Path, 'open', count_open):
                    with self.assertRaisesRegex(ValueError, '[Rr]eparse|[Ss]ymlink|[Jj]unction'):
                        self.g0.load_g0_forecast_rows(alias / 'workspace', fixture.ref, NIGHT, NOW,
                                                     expected_feature_definition_sha256=definition_hash(fixture.features))
                self.assertEqual(opened, [])
            finally:
                self.assertEqual(alias.absolute().parent.resolve(), container)
                if os.name == 'nt':
                    self.assertTrue(alias.is_junction())
                    os.rmdir(alias)
                else:
                    self.assertTrue(alias.is_symlink())
                    alias.unlink()
                self.assertEqual(sentinel.read_bytes(), b'external evidence preserved')

    def test_parent_context_accounts_prior_reads_and_tightens_caps(self):
        context = pi.ProspectiveReadContext(30.0, 3 * 1024**3)
        context.account(123)
        result = self.call(load=True, _read_context=context)
        receipt = result['receipt']
        self.assertEqual(receipt['actual_read_bytes'], context.bytes_read)
        self.assertEqual(receipt['validation_read_bytes'], context.bytes_read - 123)
        self.assertEqual(context.max_bytes, self.g0.MAX_TOTAL_READ_BYTES)
        with patch.object(self.g0, 'MAX_TOTAL_READ_BYTES', context.bytes_read - 1):
            with self.assertRaises(self.g0.ForecastCapacityError):
                self.call(_read_context=context)

    def test_public_transport_reader_preserves_guard_ledger_and_rescan_contract(self):
        self.assertIs(self.g0.G0ArtifactReader, self.g0._Reader)
        context = pi.ProspectiveReadContext(30.0, self.g0.MAX_TOTAL_READ_BYTES)
        reader = self.g0.G0ArtifactReader(self.root, context)
        ref = self.fixture.nodes['weather']['ref']
        value = reader.read(ref)
        self.assertEqual(value['source_kind'], 'forecast')
        self.assertEqual(reader.refs, {ref['path']: ref})
        reader.rescan()
        self.assertEqual(context.bytes_read, 2 * ref['size_bytes'])

    def test_transport_rescan_retains_the_smallest_per_path_byte_cap(self):
        context = pi.ProspectiveReadContext(30.0, 1000000)
        reader = self.g0.G0ArtifactReader(self.root, context)
        ref = base_ref(self.root, 'features/small.json', b'{"v":1}')
        with patch.object(self.g0, 'MAX_SMALL_BYTES', 32):
            reader.read(ref, small=True)
            (self.root / ref['path']).write_bytes(b' ' * 33)
            with self.assertRaises(self.g0.ForecastCapacityError):
                reader.rescan()

    def test_same_code_identity_cannot_carry_conflicting_required_readiness(self):
        features = copy.deepcopy(self.fixture.features)
        second = copy.deepcopy(features[0])
        second['name'] = 'other_forecast'
        second['code_ref']['readiness']['audited_at'] = NIGHT + 'T17:10:00+09:00'
        second['code_ref']['usable_at'] = NIGHT + 'T17:10:00+09:00'
        features.append(second)
        context = pi.ProspectiveReadContext(30.0, 1000000)
        reader = self.g0.G0ArtifactReader(self.root, context)
        with self.assertRaisesRegex(ValueError, 'code.*readiness'):
            self.g0._definitions(features, definition_hash(features), reader, datetime.fromisoformat(CUTOFF))

    def test_strict_cannot_refresh_a_parent_deadline(self):
        clock = [0.0]
        original = pi._bounded_bytes
        def expire_on_read(path, budget, check):
            raw = original(path, budget, check)
            clock[0] = 31.0
            return raw
        with patch.object(pi, 'monotonic', side_effect=lambda: clock[0]):
            context = pi.ProspectiveReadContext(30.0, self.g0.MAX_TOTAL_READ_BYTES)
            clock[0] = 25.0
            with patch.object(pi, '_bounded_bytes', side_effect=expire_on_read):
                with self.assertRaises(TimeoutError):
                    self.call(load=True, _read_context=context, budget_seconds=300)

    def test_strict_source_size_over_cap_is_capacity_not_invalid_evidence(self):
        ref = dict(self.fixture.ref, size_bytes=pi.MAX_SOURCE_BYTES + 1)
        with self.assertRaises(self.g0.ForecastCapacityError):
            self.g0.validate_g0_forecast(self.root, ref, NIGHT, NOW,
                                         expected_feature_definition_sha256=definition_hash(self.fixture.features))

    def test_unknown_fields_reject_in_every_defined_envelope(self):
        selectors = [
            lambda f: f.manifest,
            lambda f: f.manifest['readiness'],
            lambda f: f.policy,
            lambda f: f.features[0],
            lambda f: f.features[0]['code_ref'],
            lambda f: f.nodes['weather'],
            lambda f: f.nodes['weather']['ref'],
            lambda f: f.manifest['shards'][0],
            lambda f: f.objects[f.nodes['domain']['ref']['path']],
            lambda f: f.objects[f.nodes['weather']['ref']['path']],
            lambda f: f.objects[f.nodes['c0t0-s']['ref']['path']],
            lambda f: f.objects[f.nodes['c0t0-u']['ref']['path']],
            lambda f: f.objects[f.nodes['c0t0-u']['ref']['path']]['rows'][0],
            lambda f: f.objects[f.nodes['c0t0-f']['ref']['path']],
            lambda f: f.objects[f.nodes['c0t0-v']['ref']['path']],
        ]
        for index, select in enumerate(selectors):
            with self.subTest(envelope=index):
                self.fixture = SyntheticContract(self.root)
                select(self.fixture)['unrecognized_permission'] = True
                # Preserve an intentionally malformed ref instead of repairing it.
                if index == 6:
                    self.fixture.manifest_only()
                else:
                    self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call(load=True)

    def test_duplicate_json_keys_reject_at_root_and_nested_depth(self):
        original = (self.root / self.fixture.ref['path']).read_bytes()
        for bad, good in [(b'"usable_at":"2099-01-01T00:00:00Z",', b'"usable_at":'),
                          (b'"audited_at":"2099-01-01T00:00:00Z",', b'"audited_at":')]:
            with self.subTest(key=good):
                raw = original.replace(good, bad + good, 1)
                self.fixture.ref = base_ref(self.root, self.fixture.ref['path'], raw)
                with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
                    self.call()
        self.fixture.publish()
        node = self.fixture.nodes['weather']
        raw = canonical_bytes(self.fixture.objects[node['ref']['path']])
        raw = raw.replace(b'"data":', b'"data":{"nested":{"label":1,"label":0}},"data":', 1)
        self.fixture.overwrite_node_raw('weather', raw)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            self.call()

    def test_nonfinite_source_json_and_boolean_feature_values_reject(self):
        source = self.fixture.objects[self.fixture.nodes['weather']['ref']['path']]
        source['data'] = {'value': float('nan')}
        self.fixture.overwrite_node_raw('weather', json.dumps(source, allow_nan=True).encode())
        with self.assertRaisesRegex(ValueError, 'JSON|compliant|range'):
            self.call()
        self.fixture = SyntheticContract(self.root)
        feature = self.fixture.objects[self.fixture.nodes['c0t0-f']['ref']['path']]
        feature['values'] = {key: True for key in feature['values']}
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'numeric'):
            self.call(load=True)

    def test_bool_cell_partition_size_and_coordinate_reject(self):
        changes = [lambda f: f.cells[0].__setitem__(0, True),
                   lambda f: f.manifest['cell_partitions'][0].__setitem__(0, False),
                   lambda f: f.objects[f.nodes['c0t0-u']['ref']['path']]['rows'][0].__setitem__('utm_x_m', True)]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.fixture = SyntheticContract(self.root)
                change(self.fixture)
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call()
        ref = dict(self.fixture.ref, size_bytes=True)
        with self.assertRaises(ValueError):
            self.g0.validate_g0_forecast(self.root, ref, NIGHT, NOW,
                                         expected_feature_definition_sha256=definition_hash(self.fixture.features))

    def test_unsorted_duplicate_and_off_physical_grid_domains_reject(self):
        for cells in [[[4000, 30000], [4000, 30000]], [[4001, 30000], [4000, 30000]],
                      [[4000.5, 30000], [4001, 30000]]]:
            with self.subTest(cells=cells):
                domain = self.fixture.objects[self.fixture.nodes['domain']['ref']['path']]
                domain['cells'] = cells
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call()

    def test_duplicate_rectangle_reused_artifact_and_physical_row_reject(self):
        changes = [lambda f: f.manifest['shards'][1].__setitem__('time_partition', 0),
                   lambda f: f.manifest['shards'][1].__setitem__('snapshot_id', 'c0t0-s'),
                   lambda f: f.objects[f.nodes['c1t0-u']['ref']['path']]['rows'].__setitem__(
                       0, copy.deepcopy(f.objects[f.nodes['c0t0-u']['ref']['path']]['rows'][0]))]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.fixture = SyntheticContract(self.root)
                change(self.fixture)
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call(load=True)

    def test_missing_and_extra_validity_rows_and_source_bindings_reject(self):
        changes = [lambda v: v['rows'].clear(),
                   lambda v: v['rows'].__setitem__('extra', {}),
                   lambda v: v['feature_sources'].__setitem__('rain_3h_mm', ['c1t0-f']),
                   lambda v: next(iter(v['rows'].values())).__setitem__('extra_feature', {'start': START, 'end': END})]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.fixture = SyntheticContract(self.root)
                value = self.fixture.objects[self.fixture.nodes['c0t0-v']['ref']['path']]
                change(value)
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call()

    def test_role_source_class_and_feature_parent_spoofs_reject(self):
        changes = [lambda f: f.nodes['weather'].__setitem__('role', 'label'),
                   lambda f: f.nodes['roads'].__setitem__('source_class', 'auxiliary'),
                   lambda f: f.nodes['c0t0-f'].__setitem__('parents', ['roads']),
                   lambda f: f.nodes['c0t0-u'].__setitem__('parents', ['weather']),
                   lambda f: f.nodes['weather'].__setitem__('allowed_use', 'LABEL_ONLY')]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.fixture = SyntheticContract(self.root)
                change(self.fixture)
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call()

    def test_policy_replacement_and_names_only_expected_digest_reject(self):
        policy = json.loads((self.root / POLICY).read_bytes())
        policy['production_authorized'] = True
        self.fixture.policy.update(base_ref(self.root, POLICY, canonical_bytes(policy)))
        self.fixture.manifest_only()
        with self.assertRaisesRegex(ValueError, 'policy'):
            self.call()
        self.fixture = SyntheticContract(self.root)
        with self.assertRaisesRegex(ValueError, 'definition'):
            self.g0.validate_g0_forecast(self.root, self.fixture.ref, NIGHT, NOW,
                                         expected_feature_definition_sha256=digest(['rain_3h_mm']))

    def test_code_readiness_and_late_raw_issue_time_reject(self):
        self.fixture.features[0]['code_ref']['readiness']['audited_at'] = NIGHT + 'T17:10:00+09:00'
        self.fixture.features[0]['code_ref']['usable_at'] = NIGHT + 'T17:10:00+09:00'
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'usable_at'):
            self.call()
        self.fixture = SyntheticContract(self.root)
        self.fixture.nodes['weather']['event_time'] = CUTOFF
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'event|issue'):
            self.call()

    def test_raw_event_cannot_follow_any_required_readiness_stage(self):
        for stage in sorted(pi.READINESS_FIELDS):
            with self.subTest(stage=stage):
                self.fixture = SyntheticContract(self.root)
                node = self.fixture.nodes['weather']
                node['event_time'] = NIGHT + 'T16:59:00+09:00'
                node['readiness'][stage] = NIGHT + 'T16:58:00+09:00'
                self.fixture.objects[node['ref']['path']]['event_time'] = node['event_time']
                self.fixture.publish()
                with self.assertRaisesRegex(ValueError, 'event|issue|causal'):
                    self.call(load=True)

    def test_final_receipt_hashing_cannot_escape_absolute_deadline(self):
        original = self.g0.digest
        for collect in (False, True):
            with self.subTest(collect=collect):
                clock = [0.0]
                def expire_on_receipt_hash(value):
                    result = original(value)
                    if value == ['rain_3h_mm']:
                        clock[0] = 301.0
                    return result
                with patch.object(pi, 'monotonic', side_effect=lambda: clock[0]), \
                        patch.object(self.g0, 'digest', side_effect=expire_on_receipt_hash):
                    with self.assertRaises(TimeoutError):
                        self.call(load=collect)

    def test_caller_manifest_ref_mutation_cannot_rewrite_validated_receipt(self):
        expected = dict(self.fixture.ref)
        original = self.g0.G0ArtifactReader.rescan
        def mutate_caller_after_rescan(reader):
            original(reader)
            self.fixture.ref['sha256'] = 'f' * 64
        with patch.object(self.g0.G0ArtifactReader, 'rescan', mutate_caller_after_rescan):
            result = self.call(load=True)
        self.assertEqual(result['receipt']['manifest_ref'], expected)
        self.assertEqual(result['receipt']['consumed_sha256'][expected['path']], expected['sha256'])

    def test_transport_freezes_reference_primitives_before_read_callbacks(self):
        reference = dict(self.fixture.nodes['weather']['ref'])
        expected = dict(reference)
        original = pi._bounded_bytes
        context = pi.ProspectiveReadContext(30.0, 1000000)
        reader = self.g0.G0ArtifactReader(self.root, context)
        def mutate_caller_after_read(path, budget, check):
            raw = original(path, budget, check)
            reference.update(path='features/other.json', sha256='f' * 64, size_bytes=1)
            return raw
        with patch.object(pi, '_bounded_bytes', side_effect=mutate_caller_after_read):
            value = reader.read(reference)
        self.assertEqual(value['source_kind'], 'forecast')
        self.assertEqual(reader.refs, {expected['path']: expected})

    def test_manifest_cutoff_cannot_replace_a_different_shard_cutoff(self):
        self.fixture.manifest['cutoff_time'] = NIGHT + 'T17:30:00+09:00'
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'cutoff|night'):
            self.call(load=True)

    def test_model_projection_rejects_instead_of_rewriting_raw_scope(self):
        result = self.call(load=True)
        row = result['rows'][0]
        for changed in [dict(row, cutoff_time=NIGHT + 'T17:30:00+09:00'),
                        dict(row, operational_night='2026-10-13')]:
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(ValueError, 'cutoff|night'):
                    self.g0._model_row(changed, datetime.fromisoformat(CUTOFF))

    def test_malformed_enum_and_domain_identity_are_invalid_contract_errors(self):
        changes = [lambda f: f.features[0].__setitem__('deployment', []),
                   lambda f: f.nodes['weather'].__setitem__('source_class', []),
                   lambda f: f.nodes['weather'].__setitem__('role', []),
                   lambda f: f.nodes['weather'].__setitem__('allowed_use', []),
                   lambda f: f.manifest.__setitem__('domain_id', [])]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.fixture = SyntheticContract(self.root)
                change(self.fixture)
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call()

    def test_model_target_and_qualification_field_names_are_not_numeric_predictors(self):
        from models.research_selection import OUTCOME_FEATURES
        for name in sorted(OUTCOME_FEATURES):
            with self.subTest(name=name):
                features = copy.deepcopy(self.fixture.features)
                features[0]['name'] = name
                reader = self.g0.G0ArtifactReader(self.root, pi.ProspectiveReadContext(30.0, 1000000))
                with self.assertRaisesRegex(ValueError, 'target|outcome'):
                    self.g0._definitions(features, definition_hash(features), reader, datetime.fromisoformat(CUTOFF))

    def test_strict_uses_owned_join_and_reads_each_artifact_twice(self):
        from collections import Counter
        reads = Counter()
        original = pi._bounded_bytes
        def count_reads(path, budget, check):
            raw = original(path, budget, check)
            reads[path.relative_to(self.root).as_posix()] += 1
            return raw
        with patch.object(pi, "load_prospective_inputs", side_effect=AssertionError("Nested file loader")), \
                patch.object(pi, "_bounded_bytes", side_effect=count_reads):
            result = self.call(load=True)
        self.assertEqual(set(reads), set(result['receipt']['consumed_sha256']))
        self.assertEqual(set(reads.values()), {2})
        expected = 2 * sum((self.root / path).stat().st_size for path in reads)
        self.assertEqual(result['receipt']['validation_read_bytes'], expected)

    def test_shard_byte_preflight_preserves_legacy_384mib_scan_budget(self):
        check = getattr(self.g0, '_check_shard_bytes', None)
        self.assertTrue(callable(check), 'Per-shard input-byte preflight is missing')
        refs = [dict(path=f'features/f{x}.json', sha256='a' * 64, size_bytes=size)
                for x, size in enumerate([1024**2, 127 * 1024**2, 128 * 1024**2, 128 * 1024**2])]
        self.assertEqual(check(refs), pi.MAX_TOTAL_BYTES)
        refs[1]['size_bytes'] += 1
        with self.assertRaises(self.g0.ForecastCapacityError):
            check(refs)

    def test_transport_growth_after_stat_is_bounded_by_the_declared_exact_size(self):
        ref = base_ref(self.root, 'features/growth.json', b'{"v":1}')
        original = Path.open
        target = self.root / ref['path']
        def grow_before_open(path, mode='r', *args, **kwargs):
            if path == target and mode == 'rb':
                with original(path, 'wb') as stream:
                    stream.write(b'x' * 100000)
            return original(path, mode, *args, **kwargs)
        context = pi.ProspectiveReadContext(30.0, 1000000)
        reader = self.g0.G0ArtifactReader(self.root, context)
        with patch.object(Path, 'open', grow_before_open), self.assertRaises(ValueError):
            reader.read(ref)
        self.assertEqual(context.bytes_read, ref['size_bytes'] + 1)

    def test_asof_equality_rejects_and_utc_aliases_preserve_same_rows(self):
        with self.assertRaisesRegex(ValueError, 'Horizon'):
            self.g0.validate_g0_forecast(self.root, self.fixture.ref, NIGHT, datetime.fromisoformat(START),
                                         expected_feature_definition_sha256=definition_hash(self.fixture.features))
        before = self.call(load=True)
        self.fixture.manifest['horizon'] = dict(start='2026-10-14T10:00:00Z', end='2026-10-14T10:20:00Z')
        for node in self.fixture.nodes.values():
            if node['source_kind'] == 'forecast_universe':
                for row in self.fixture.objects[node['ref']['path']]['rows']:
                    row['window_start_jst'] = datetime.fromisoformat(row['window_start_jst']).astimezone(timezone.utc).isoformat()
        self.fixture.publish()
        after = self.call(load=True)
        self.assertEqual(before['rows'], after['rows'])
        self.assertEqual(before['receipt']['canonical_joined_rows_sha256'], after['receipt']['canonical_joined_rows_sha256'])

    def test_window_ending_next_0700_is_half_open_and_accepted(self):
        first = datetime.fromisoformat('2026-10-15T06:40:00+09:00')
        interval = dict(start=first.isoformat(), end='2026-10-15T07:00:00+09:00')
        self.fixture.manifest['horizon'] = interval
        for node in self.fixture.nodes.values():
            node['valid_time'] = interval.copy()
            value = self.fixture.objects[node['ref']['path']]
            if node['source_kind'] in {'static', 'forecast'}:
                value['valid_time'] = interval.copy()
        for ci in range(2):
            for ti in range(2):
                sid = f'c{ci}t{ti}'
                unit = self.fixture.objects[self.fixture.nodes[sid + '-u']['ref']['path']]['rows'][0]
                old = unit['row_id']
                stamp = first + timedelta(minutes=10 * ti)
                unit.update(row_id=row_id(self.fixture.cells[ci], stamp), window_start_jst=stamp.isoformat())
                feature = self.fixture.objects[self.fixture.nodes[sid + '-f']['ref']['path']]
                feature['values'] = {unit['row_id']: feature['values'][old]}
                sidecar = self.fixture.objects[self.fixture.nodes[sid + '-v']['ref']['path']]
                sidecar['rows'] = {unit['row_id']: {'rain_3h_mm': interval.copy()}}
        self.fixture.publish()
        result = self.call(load=True)
        self.assertEqual(len(result['rows']), 4)
        self.assertEqual(result['receipt']['window_count'], 2)

    def test_graph_and_whole_domain_capacity_caps_are_explicit(self):
        for field, limit in [('MAX_SOURCE_NODES', 1), ('MAX_SOURCE_EDGES', 1), ('MAX_DOMAIN_CELLS', 1),
                             ('MAX_WINDOWS', 1), ('MAX_DOMAIN_ROWS', 3), ('MAX_SHARDS', 3), ('MAX_SMALL_BYTES', 1)]:
            with self.subTest(field=field), patch.object(self.g0, field, limit):
                with self.assertRaises(self.g0.ForecastCapacityError):
                    self.call()

    def test_missing_or_overlapping_partition_and_missing_shard_reject(self):
        for key, value in [('cell_partitions', [[0, 1]]), ('time_partitions', [[0, 2], [1, 2]]),
                           ('shards', self.fixture.manifest['shards'][:-1])]:
            with self.subTest(key=key):
                old = self.fixture.manifest[key]
                self.fixture.manifest[key] = value
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call()
                self.fixture.manifest[key] = old

    def test_required_readiness_equality_and_omission_reject(self):
        for value in [CUTOFF, None]:
            with self.subTest(value=value):
                node = self.fixture.nodes['weather']
                if value is None:
                    node['readiness'].pop('audited_at', None)
                else:
                    node['readiness']['audited_at'] = value
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call()

    def test_usable_at_cannot_ignore_parent_readiness(self):
        self.fixture.nodes['weather']['readiness']['audited_at'] = NIGHT + 'T17:10:00+09:00'
        self.fixture.nodes['weather']['usable_at'] = NIGHT + 'T17:10:00+09:00'
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'usable_at'):
            self.call()

    def test_snapshot_binding_and_per_row_physical_validity_reject(self):
        path = self.fixture.nodes['c0t0-v']['ref']['path']
        validity = self.fixture.objects[path]
        first = next(iter(validity['rows'].values()))
        first['rain_3h_mm']['end'] = NIGHT + 'T19:05:00+09:00'
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'valid'):
            self.call(load=True)

    def test_definition_units_and_code_identity_are_bound(self):
        self.fixture.features[0]['units'] = 'inches'
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'definition'):
            self.call()

    def test_planned_and_lagged_are_capability_blocked_not_prohibited_policy(self):
        for kind in ['planned_effort', 'lagged_observation']:
            with self.subTest(kind=kind):
                self.fixture.nodes['weather']['source_kind'] = kind
                self.fixture.publish()
                with self.assertRaises(self.g0.ForecastCapabilityError):
                    self.call()

    def test_untyped_outcomes_and_raw_trajectory_roles_reject(self):
        for kind in ['actual_trajectory', 'heldout_outcome', 'sealed_confirmation', 'untyped_target_projection']:
            with self.subTest(kind=kind):
                self.fixture.nodes['weather']['source_kind'] = kind
                self.fixture.publish()
                with self.assertRaises(ValueError) as caught:
                    self.call()
                self.assertNotIsInstance(caught.exception, self.g0.ForecastCapabilityError)

    def test_receipt_validation_does_not_grant_large_domain_model_support(self):
        with patch.object(self.g0, 'MAX_MODEL_ROWS', 3):
            receipt = self.call()
            self.assertEqual(receipt['row_count'], 4)
            with self.assertRaises(self.g0.ForecastCapacityError):
                self.call(load=True)

    def test_collector_byte_limit_never_truncates(self):
        with patch.object(self.g0, 'MAX_MODEL_ROW_BYTES', 1):
            with self.assertRaises(self.g0.ForecastCapacityError):
                self.call(load=True)

    def test_whole_operation_actual_read_ledger_includes_legacy_rescans(self):
        raw_total = [0]
        original = pi._bounded_bytes
        def count_read(target, budget, check):
            raw = original(target, budget, check)
            raw_total[0] += len(raw)
            return raw
        with patch.object(pi, '_bounded_bytes', side_effect=count_read):
            result = self.call(load=True)
        self.assertEqual(result['receipt']['actual_read_bytes'], raw_total[0])
        self.assertGreater(raw_total[0], 3 * sum((self.root / self.fixture.nodes[x]['ref']['path']).stat().st_size
                                               for x in self.fixture.snapshots))
        with patch.object(self.g0, 'MAX_TOTAL_READ_BYTES', raw_total[0] - 1):
            with self.assertRaises(self.g0.ForecastCapacityError):
                self.call(load=True)

    def test_final_rescan_mutation_returns_no_partial_rows(self):
        original = self.g0._Reader.rescan
        target = self.root / self.fixture.nodes['weather']['ref']['path']
        def change_then_rescan(reader):
            target.write_bytes(target.read_bytes() + b' ')
            return original(reader)
        with patch.object(self.g0._Reader, 'rescan', change_then_rescan):
            with self.assertRaisesRegex(ValueError, 'hash|changed|size'):
                self.call(load=True)


class SyntheticOsmContract(SyntheticContract):
    """Explicitly synthetic archive; expected identities are patched only in tests."""
    def __init__(self, root):
        self.proof = None
        super().__init__(root)
        columns = ['cell_id', 'cell_x_index', 'cell_y_index', 'cell_center_x', 'cell_center_y',
                   'normal_route', 'road_length_m', 'road_direction_deg', 'candidate_source', 'island_name']
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for index, cell in enumerate(self.cells):
            writer.writerow(dict(zip(columns, [f'utm52n_100m_{cell[0]}_{cell[1]}', cell[0], cell[1],
                                                cell[0] * 100 + 50, cell[1] * 100 + 50, 'True',
                                                10 * (index + 1), 15, 'osm_auxiliary', '奄美大島'])))
        self.csv = stream.getvalue().encode()
        memory = io.BytesIO()
        self.member = '04_processed_road/osm_road_candidate_cells.csv'
        with zipfile.ZipFile(memory, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(self.member, self.csv)
        self.archive = memory.getvalue()
        encoded = base64.b64encode(self.archive)
        self.chunk_size = (len(encoded) - 1) // 32
        part_ids = []
        for index in range(33):
            identifier = f'part-{index:03d}'
            part_ids.append(identifier)
            raw = encoded[index * self.chunk_size:(index + 1) * self.chunk_size] if index < 32 else encoded[32 * self.chunk_size:]
            path = f'artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts/part_{index:03d}.b64'
            self.add(identifier, path, 'osm_archive_part', 'protocol', [], {})
            self.objects[path] = raw
            self.nodes[identifier]['valid_time'] = None
        self.add('csv', 'data/processed/osm/cells.csv', 'osm_road_cells_csv', 'protocol', part_ids, {})
        self.objects[self.nodes['csv']['ref']['path']] = self.csv
        self.nodes['csv']['valid_time'] = None
        code = bound(base_ref(root, 'scripts/build_osm_prospective_universe.py', b'# synthetic projection code identity\n'))
        feature = self.features[0]
        feature.update(name='road_length_m', units='m', deployment='static_predictor', required_source_ids=['length'], code_ref=code)
        del self.nodes['weather']
        self.nodes['roads'].update(source_kind='osm_static_projection', parents=['csv'], event_time=None)
        self.objects[self.nodes['roads']['ref']['path']] = dict(schema_version='habu-g0-osm-static-projection-v1',
                                                                operation='candidate_cells', version='1',
                                                                source_csv_node_id='csv', code_ref=code)
        descriptor = dict(schema_version='habu-g0-osm-static-projection-v1', operation='road_length_m', version='1',
                          source_csv_node_id='csv', code_ref=code)
        self.add('length', 'features/sources/length.json', 'osm_static_projection', 'feature', ['csv'], descriptor)
        for node in self.nodes.values():
            node['source_class'] = 'auxiliary'
            if node['source_kind'] == 'feature_values':
                node['parents'] = ['length']
                value = self.objects[node['ref']['path']]
                value.update(feature_name='road_length_m', use_role='static_predictor')
                value['values'] = {key: 10.0 if key.startswith('4000:') else 20.0 for key in value['values']}
            elif node['source_kind'] == 'validity':
                value = self.objects[node['ref']['path']]
                value['feature_sources'] = {'road_length_m': next(iter(value['feature_sources'].values()))}
                value['rows'] = {key: {'road_length_m': next(iter(fields.values()))} for key, fields in value['rows'].items()}
            elif node['source_kind'] == 'snapshot':
                self.objects[node['ref']['path']]['feature_schema_sha256'] = digest(['road_length_m'])
        self.objects[self.nodes['domain']['ref']['path']]['source_class'] = 'auxiliary'
        self.proof = dict(schema_version='habu-g0-osm-current-intake-v1', purpose='CURRENT_RUN_BYTE_EXACT_REINGESTION',
                          source_git_sha='a' * 40, started_at=NIGHT + 'T16:30:00+09:00', parts_completed_at=READY,
                          parts=[], archive_sha256=hashlib.sha256(self.archive).hexdigest(), archive_size_bytes=len(self.archive),
                          member_path=self.member, csv_sha256=hashlib.sha256(self.csv).hexdigest(), csv_size_bytes=len(self.csv),
                          historical_access='NOT_ATTESTED', source_authenticity='NOT_ATTESTED')
        self.publish()

    def publish(self):
        for identifier, node in self.nodes.items():
            if identifier not in self.snapshots:
                value = self.objects[node['ref']['path']]
                raw = value if isinstance(value, bytes) else canonical_bytes(value) + b'\n'
                node['ref'] = base_ref(self.root, node['ref']['path'], raw)
        if self.proof is not None:
            self.proof['parts'] = [{key: node[key] for key in ('id', 'ref', 'readiness', 'usable_at')}
                                   for node in self.nodes.values() if node['source_kind'] == 'osm_archive_part']
            ref = base_ref(self.root, 'features/osm-provenance.json', canonical_bytes(self.proof) + b'\n')
            self.nodes['csv']['provenance_ref'] = bound(ref)
        for identifier in self.snapshots:
            node = self.nodes[identifier]
            snap = self.objects[node['ref']['path']]
            for ref in [snap['universe'], *snap['features']]:
                ref.update(next(dict(n['ref'], available_at=READY) for n in self.nodes.values() if n['ref']['path'] == ref['path']))
            node['ref'] = base_ref(self.root, node['ref']['path'], canonical_bytes(snap) + b'\n')
        self.manifest['feature_definition_sha256'] = definition_hash(self.features)
        self.manifest_only()


class OsmTypedContractTests(unittest.TestCase):
    def setUp(self):
        self.g0 = importlib.import_module('g0_forecast_contract')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = SyntheticOsmContract(self.root)
        fixture = self.fixture
        patcher = patch.multiple(self.g0, create=True, OSM_ARCHIVE_SHA256=hashlib.sha256(fixture.archive).hexdigest(),
                                 OSM_ARCHIVE_BYTES=len(fixture.archive), OSM_CSV_SHA256=hashlib.sha256(fixture.csv).hexdigest(),
                                 OSM_CSV_BYTES=len(fixture.csv), OSM_EXPECTED_CELLS=2, OSM_PART_CHUNK_BYTES=fixture.chunk_size)
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self):
        return self.g0.load_g0_forecast_rows(self.root, self.fixture.ref, NIGHT, NOW,
                                            expected_feature_definition_sha256=definition_hash(self.fixture.features))

    def test_typed_original_parts_csv_and_projection_are_all_consumed(self):
        result = self.call()
        self.assertEqual([row['features']['road_length_m'] for row in result['rows']], [10.0, 10.0, 20.0, 20.0])
        consumed = result['receipt']['consumed_sha256']
        self.assertTrue(all(node['ref']['path'] in consumed for node in self.fixture.nodes.values()))
        self.assertIn('features/osm-provenance.json', consumed)
        self.assertEqual(set(result['receipt']['source_class_by_path'].values()), {'auxiliary'})
        self.assertFalse(result['receipt']['fit_authorized'])

    def test_original_part_mutation_cannot_be_hidden_by_updating_declared_hashes(self):
        node = self.fixture.nodes['part-000']
        self.fixture.objects[node['ref']['path']] = b'A' * len(self.fixture.objects[node['ref']['path']])
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'archive|ZIP|base64'):
            self.call()

    def test_missing_original_part_is_not_an_opaque_csv_raw_source(self):
        del self.fixture.nodes['part-032']
        self.fixture.nodes['csv']['parents'].remove('part-032')
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, '33|part|archive'):
            self.call()

    def test_derived_csv_must_equal_the_exact_archive_member(self):
        path = self.fixture.nodes['csv']['ref']['path']
        self.fixture.objects[path] = self.fixture.csv.replace(b'10,15', b'11,15')
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'CSV|csv|member'):
            self.call()

    def test_projection_values_are_recomputed_instead_of_trusting_metadata(self):
        path = self.fixture.nodes['c0t0-f']['ref']['path']
        value = self.fixture.objects[path]
        value['values'] = {key: 999 for key in value['values']}
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'projection|CSV|csv'):
            self.call()

    def test_archived_domain_cannot_be_narrowed_to_one_cell(self):
        self.fixture.objects[self.fixture.nodes['domain']['ref']['path']]['cells'] = [[4000, 30000]]
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'domain|CSV|projection'):
            self.call()

    def test_typed_transport_does_not_gain_official_class_or_fake_event_validity(self):
        for key, value in [('source_class', 'official'), ('event_time', READY),
                           ('valid_time', {'start': START, 'end': END})]:
            with self.subTest(key=key):
                node = self.fixture.nodes['part-000']
                old = node[key]
                node[key] = value
                self.fixture.publish()
                with self.assertRaises(ValueError):
                    self.call()
                node[key] = old

    def test_missing_current_run_provenance_is_blocked(self):
        self.fixture.nodes['csv'].pop('provenance_ref')
        self.fixture.manifest_only()
        with self.assertRaises(ValueError):
            self.call()

    def test_current_reingestion_cannot_claim_authenticated_historical_access(self):
        self.fixture.proof['historical_access'] = 'ATTESTED'
        self.fixture.publish()
        with self.assertRaisesRegex(ValueError, 'historical|provenance|authentic'):
            self.call()

    def test_generic_static_source_namespace_stays_closed_to_original_parts(self):
        with self.assertRaisesRegex(ValueError, 'namespace'):
            self.g0._input_ref(self.fixture.nodes['part-000']['ref'])


if __name__ == '__main__':
    unittest.main()
