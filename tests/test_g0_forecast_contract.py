"""Synthetic strict G0 contracts: software consistency, never scientific evidence."""
import copy
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
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


if __name__ == '__main__':
    unittest.main()
