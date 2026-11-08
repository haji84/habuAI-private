"""Synthetic declaration checks; none authenticate observations or permit fitting."""
import copy
import hashlib
import importlib
import json
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from tests.test_research_selection import selection_fixture, bind_selection

READY = '2026-09-30T00:00:00+09:00'
TARGET = 'OWNER_CAPTURED_HABU_INDIVIDUALS_DURING_MEASURED_ACTIVE_SEARCH'


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def seal(projection):
    projection['projection_sha256'] = sha({key: value for key, value in projection.items() if key != 'projection_sha256'})
    return projection


def fixture():
    selection = selection_fixture()
    nodes = {}
    for identifier, role, family, char in [('outcomes', 'label', 'count', '1'),
            ('complete', 'complete_outcome', 'count', '2'),
            ('measured', 'search_evidence', 'effort', '3'),
            ('active', 'active_search', 'effort', '4')]:
        path = 'evidence/synthetic-' + identifier + '.json'
        selection['source_sha256'][path] = char * 64
        selection['source_received_at'][path] = READY
        nodes[identifier] = dict(id=identifier, ref=dict(path=path, sha256=char * 64, size_bytes=128),
                                 source_role=role, source_kind='RAW', parents=[],
                                 readiness={key: READY for key in ('source_received_at', 'derived_at', 'materialized_at', 'audited_at')},
                                 usable_at=READY)
    bind_selection(selection)
    common = dict(selection_sha256=selection['selection_sha256'], corpus_sha256=selection['corpus_sha256'],
                  target=TARGET, owner_id='synthetic-owner', observer_id='synthetic-observer', method_version='independent-clock-v1',
                  readiness=copy.deepcopy(nodes['outcomes']['readiness']), usable_at=READY)
    count = dict(common, schema_version='habu-count-ledger-projection-v1', units='individuals',
                 source_nodes=[nodes['outcomes'], nodes['complete']], rows=[])
    effort = dict(common, schema_version='habu-active-search-effort-projection-v1', units='active_search_seconds',
                  source_nodes=[nodes['measured'], nodes['active']], rows=[])
    for index, row in enumerate(selection['accepted']):
        unit = {key: row[key] for key in ('row_id', 'night', 'cell_x', 'cell_y', 'window_start_jst')}
        start = row['window_start_jst']
        interval = {'start': start.replace('20:00:00', '20:05:00') if index % 2 else start,
                    'end': start.replace('20:00:00', '20:10:00' if index % 2 else '20:05:00')}
        scope = dict(unit, owner_id=common['owner_id'], observer_id=common['observer_id'],
                     method_version=common['method_version'], active_intervals=[interval])
        events = [dict(event_id=event, event_time=start.replace('20:00:00', '20:07:00' if index % 2 else '20:02:00'),
                       individual_ids=[event + '-animal-a', event + '-animal-b'], outcome_source_ids=['outcomes'])
                  for event in row['capture_event_ids']]
        count['rows'].append(dict(unit, count=2 if row['label'] else 0, events=events,
                         individual_source_ids=['outcomes'] if events else [],
                         complete_scope=dict(scope, declaration='DECLARED_COMPLETE', source_ids=['complete'])))
        effort['rows'].append(dict(unit, active_search_seconds=300, active_intervals=[interval],
                          measurement_source_ids=['measured'],
                          active_scope=dict(scope, declaration='DECLARED_ACTIVE_SEARCH', source_ids=['active'])))
    return selection, seal(count), seal(effort)


class CountFeasibilityTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('models.count_feasibility')
        self.selection, self.count, self.effort = fixture()

    def call(self, **kwargs):
        return self.module.assess_count_feasibility(self.selection, self.count, self.effort, **kwargs)

    def reseal(self):
        seal(self.count)
        seal(self.effort)

    def test_missing_projections_do_not_convert_binary_labels_or_event_ids_to_counts(self):
        result = self.module.assess_count_feasibility(self.selection)
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertIsNone(result['summary']['declared_individual_count'])

    def test_two_individuals_in_one_event_remain_two_without_any_authority(self):
        result = self.call()
        self.assertEqual(result['status'], 'DECLARED_CONSISTENCY_ONLY')
        self.assertEqual(result['summary']['declared_individual_count'], 6)
        self.assertEqual(result['summary']['declared_active_search_seconds'], 1800)
        self.assertEqual(result['statistical_adequacy'], 'NOT_ASSESSED')
        self.assertEqual(result['source_authentication'], 'CALLER_DEPENDENCY_REQUIRED')
        self.assertEqual(result['source_authenticity'], 'NOT_ATTESTED')
        for key in ('fit_authorized', 'scientific_execution_authorized', 'official_issuance_authorized', 'production_authorized'):
            self.assertIs(result[key], False)
        self.assertIn('EVENT_GEOLOCATION_NOT_REATTESTED', result['limitations'])

    def test_complete_scoped_zero_is_distinct_from_unknown_count_or_coverage(self):
        for change in ('count', 'scope', 'individuals'):
            with self.subTest(change=change):
                self.selection, self.count, self.effort = fixture()
                if change == 'count':
                    self.count['rows'][1]['count'] = None
                elif change == 'scope':
                    self.count['rows'][0]['complete_scope'] = None
                else:
                    self.count['rows'][0]['events'][0]['individual_ids'] = None
                self.reseal()
                self.assertEqual(self.call()['status'], 'NEED_MORE_DATA')

    def test_explicit_count_is_not_event_count_and_is_never_auto_filled(self):
        self.count['rows'][0]['count'] = 1
        self.reseal()
        with self.assertRaises(ValueError):
            self.call()
        self.count['rows'][0]['count'] = None
        self.reseal()
        self.assertEqual(self.call()['status'], 'NEED_MORE_DATA')

    def test_duplicate_individual_or_event_is_rejected(self):
        for key in ('individual', 'event'):
            self.selection, self.count, self.effort = fixture()
            first, second = self.count['rows'][0]['events'][0], self.count['rows'][2]['events'][0]
            if key == 'individual':
                second['individual_ids'][0] = first['individual_ids'][0]
            else:
                second['event_id'] = first['event_id']
            self.reseal()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.call()

    def test_unknown_or_zero_effort_never_yields_rate_or_partial_fit_rows(self):
        for seconds in (None, 0):
            self.selection, self.count, self.effort = fixture()
            self.effort['rows'][0].update(active_search_seconds=seconds, active_intervals=[], active_scope=None)
            self.reseal()
            result = self.call()
            self.assertEqual(result['status'], 'NEED_MORE_DATA')
            self.assertIsNone(result['summary']['declared_active_search_seconds'])
            self.assertNotIn('rows', result)
            self.assertNotIn('rate', result)

    def test_positive_also_requires_complete_outcomes_and_measured_search_scope(self):
        for target in ('count', 'effort'):
            self.selection, self.count, self.effort = fixture()
            body = self.count['rows'][0] if target == 'count' else self.effort['rows'][0]
            body['complete_scope' if target == 'count' else 'active_scope'] = None
            self.reseal()
            self.assertEqual(self.call()['status'], 'NEED_MORE_DATA')

    def test_unit_owner_method_scope_and_active_interval_cannot_disagree(self):
        changes = [('cell_x', 4011), ('night', '2026-09-04'), ('window_start_jst', '2026-09-01T20:10:00+09:00')]
        for key, value in changes:
            self.selection, self.count, self.effort = fixture()
            self.count['rows'][0]['complete_scope'][key] = value
            self.reseal()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.call()
        for key in ('owner_id', 'observer_id', 'method_version', 'units', 'target'):
            self.selection, self.count, self.effort = fixture()
            self.effort[key] = 'contradictory'
            self.reseal()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.call()

    def test_event_outside_active_interval_or_at_half_open_end_is_invalid(self):
        for minute in ('10', '11'):
            self.count['rows'][0]['events'][0]['event_time'] = '2026-09-01T20:' + minute + ':00+09:00'
            self.reseal()
            with self.assertRaises(ValueError):
                self.call()

    def test_scope_duration_mismatch_and_overlapping_or_outside_intervals_are_invalid(self):
        self.effort['rows'][0]['active_search_seconds'] = 599
        self.reseal()
        with self.assertRaises(ValueError):
            self.call()
        self.effort['rows'][0]['active_search_seconds'] = 600
        self.effort['rows'][0]['active_intervals'] *= 2
        self.reseal()
        with self.assertRaises(ValueError):
            self.call()

    def test_readiness_cutoff_equality_early_measurement_and_parent_max_are_invalid(self):
        for kind in ('equality', 'early', 'parent'):
            self.selection, self.count, self.effort = fixture()
            node = self.effort['source_nodes'][0]
            if kind == 'equality':
                node['readiness'] = {key: self.selection['fit_cutoff'] for key in node['readiness']}
                node['usable_at'] = self.selection['fit_cutoff']
            elif kind == 'early':
                node['readiness'] = {key: '2026-09-01T19:00:00+09:00' for key in node['readiness']}
                node['usable_at'] = '2026-09-01T19:00:00+09:00'
            else:
                self.effort['source_nodes'][1].update(source_kind='DERIVED', parents=['measured'], usable_at='2026-09-29T00:00:00+09:00')
            self.reseal()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.call()

    def rebind_selection(self):
        bind_selection(self.selection)
        for p in (self.count, self.effort):
            p['selection_sha256'] = self.selection['selection_sha256']
        self.reseal()

    def test_each_readiness_stage_cannot_precede_the_consumed_event_or_scope(self):
        for family, index in [('count', 0), ('count', 1), ('effort', 0), ('effort', 1)]:
            for stage in ('source_received_at', 'derived_at', 'materialized_at', 'audited_at'):
                self.selection, self.count, self.effort = fixture()
                p = self.count if family == 'count' else self.effort
                node = p['source_nodes'][index]
                node['readiness'][stage] = '2026-09-01T19:59:00+09:00'
                if stage == 'source_received_at':
                    self.selection['source_received_at'][node['ref']['path']] = node['readiness'][stage]
                self.rebind_selection()
                with self.subTest(family=family, index=index, stage=stage):
                    with self.assertRaisesRegex(ValueError, 'precedes'):
                        self.call()

    def test_separate_individual_ledger_must_not_exist_before_its_capture(self):
        node = copy.deepcopy(self.count['source_nodes'][0])
        node.update(id='individuals', ref=dict(path='evidence/synthetic-individuals.json', sha256='5' * 64, size_bytes=128))
        node['readiness']['source_received_at'] = '2026-09-01T19:00:00+09:00'
        self.selection['source_sha256'][node['ref']['path']] = node['ref']['sha256']
        self.selection['source_received_at'][node['ref']['path']] = node['readiness']['source_received_at']
        self.count['source_nodes'].append(node)
        self.count['rows'][0]['individual_source_ids'] = ['individuals']
        self.rebind_selection()
        with self.assertRaisesRegex(ValueError, 'precedes'):
            self.call()

    def test_one_night_positive_only_is_not_binary_adequacy_or_fit_authority(self):
        self.selection['accepted'] = self.selection['accepted'][:1]
        self.selection.update(status='NEED_MORE_DATA', blockers=['Binary support missing'],
                              counts=dict(accepted_rows=1, rejected_rows=0, nights=1, positives=1, negatives=0))
        self.count['rows'] = self.count['rows'][:1]
        self.effort['rows'] = self.effort['rows'][:1]
        self.rebind_selection()
        result = self.call()
        self.assertEqual(result['status'], 'DECLARED_CONSISTENCY_ONLY')
        self.assertEqual(result['statistical_adequacy'], 'NOT_ASSESSED')
        self.assertFalse(result['fit_authorized'])

    def test_fanout_lineage_memberships_and_event_individual_caps_block(self):
        node = copy.deepcopy(self.count['source_nodes'][0])
        node.update(id='derived-individuals', source_kind='DERIVED', parents=['outcomes', 'complete'],
                    ref=dict(path='evidence/synthetic-derived.json', sha256='5' * 64, size_bytes=128))
        self.selection['source_sha256'][node['ref']['path']] = node['ref']['sha256']
        self.selection['source_received_at'][node['ref']['path']] = READY
        self.count['source_nodes'].append(node)
        self.count['rows'][0]['individual_source_ids'] = ['derived-individuals']
        self.rebind_selection()
        with patch.object(self.module, 'MAX_LINEAGE_MEMBERSHIPS', 3):
            with self.assertRaises(self.module.CountCapacityBlocked):
                self.call()
        for cap in ('MAX_EVENTS', 'MAX_INDIVIDUALS'):
            with self.subTest(cap=cap), patch.object(self.module, cap, 1):
                with self.assertRaises(self.module.CountCapacityBlocked):
                    self.call()

    def test_same_observer_cannot_double_count_overlapping_effort_in_other_cells(self):
        for utc_alias in (False, True):
            self.selection, self.count, self.effort = fixture()
            interval = copy.deepcopy(self.effort['rows'][0]['active_intervals'])
            if utc_alias:
                interval = [dict(start='2026-09-01T11:00:00Z', end='2026-09-01T11:05:00Z')]
            self.effort['rows'][1]['active_intervals'] = interval
            self.effort['rows'][1]['active_scope']['active_intervals'] = interval
            self.count['rows'][1]['complete_scope']['active_intervals'] = interval
            self.reseal()
            with self.subTest(utc_alias=utc_alias), self.assertRaisesRegex(ValueError, 'overlap'):
                self.call()

    def test_missing_count_does_not_hide_an_unrelated_orphan_source(self):
        node = copy.deepcopy(self.count['source_nodes'][0])
        node.update(id='orphan', ref=dict(path='evidence/synthetic-orphan.json', sha256='5' * 64, size_bytes=128))
        self.selection['source_sha256'][node['ref']['path']] = node['ref']['sha256']
        self.selection['source_received_at'][node['ref']['path']] = READY
        self.count['source_nodes'].append(node)
        self.count['rows'][0]['count'] = None
        self.rebind_selection()
        with self.assertRaisesRegex(ValueError, 'Unbound'):
            self.call()

    def test_adjacent_complete_scope_pieces_cover_measured_interval_union(self):
        self.count['rows'][0]['complete_scope']['active_intervals'] = [
            dict(start='2026-09-01T20:00:00+09:00', end='2026-09-01T20:02:00+09:00'),
            dict(start='2026-09-01T20:02:00+09:00', end='2026-09-01T20:05:00+09:00')]
        self.reseal()
        self.assertEqual(self.call()['status'], 'DECLARED_CONSISTENCY_ONLY')
        self.count['rows'][0]['complete_scope']['active_intervals'][0]['end'] = '2026-09-01T20:03:00+09:00'
        self.count['rows'][0]['complete_scope']['active_intervals'][1]['start'] = '2026-09-01T20:04:00+09:00'
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'cover'):
            self.call()

    def test_source_depth_capacity_uses_count_resource_exception(self):
        parent = 'outcomes'
        for index in range(32):
            node = copy.deepcopy(self.count['source_nodes'][0])
            node.update(id='chain-' + str(index), source_kind='DERIVED', parents=[parent],
                        ref=dict(path='evidence/chain-' + str(index) + '.json', sha256=sha(index), size_bytes=128))
            self.selection['source_sha256'][node['ref']['path']] = node['ref']['sha256']
            self.selection['source_received_at'][node['ref']['path']] = READY
            self.count['source_nodes'].append(node)
            parent = node['id']
        self.count['rows'][0]['individual_source_ids'] = [parent]
        self.rebind_selection()
        with self.assertRaises(self.module.CountCapacityBlocked):
            self.call()

    def test_derived_records_cannot_launder_any_early_readiness_of_raw_ancestors(self):
        for identifier in ('outcomes', 'individuals', 'complete', 'measured', 'active'):
            for stage in ('source_received_at', 'derived_at', 'materialized_at', 'audited_at'):
                self.selection, self.count, self.effort = fixture()
                p = self.count if identifier in ('outcomes', 'individuals', 'complete') else self.effort
                if identifier == 'individuals':
                    direct = copy.deepcopy(p['source_nodes'][0])
                    direct.update(id=identifier, ref=dict(path='evidence/individuals.json', sha256=sha(identifier), size_bytes=128))
                    self.selection['source_sha256'][direct['ref']['path']] = direct['ref']['sha256']
                    self.selection['source_received_at'][direct['ref']['path']] = READY
                    p['source_nodes'].append(direct)
                    self.count['rows'][0]['individual_source_ids'] = [identifier]
                else:
                    direct = next(n for n in p['source_nodes'] if n['id'] == identifier)
                parent = copy.deepcopy(direct)
                parent.update(id='raw-ancestor', source_role='label' if p is self.count else 'search_evidence',
                              ref=dict(path='evidence/raw-ancestor.json', sha256=sha('raw-' + identifier), size_bytes=128))
                parent['readiness'][stage] = '2026-09-01T19:59:00+09:00'
                self.selection['source_sha256'][parent['ref']['path']] = parent['ref']['sha256']
                self.selection['source_received_at'][parent['ref']['path']] = parent['readiness']['source_received_at']
                direct.update(source_kind='DERIVED', parents=[parent['id']])
                p['source_nodes'].append(parent)
                self.rebind_selection()
                with self.subTest(source=identifier, stage=stage), self.assertRaisesRegex(ValueError, 'precedes'):
                    self.call()

    def test_invalid_budget_and_effort_numeric_types_raise_valueerror(self):
        for value in (True, None, 0, -1, float('nan'), float('inf'), 10**1000):
            with self.subTest(budget=type(value)), self.assertRaises(ValueError):
                self.call(budget_seconds=value)
        for value in (True, -1, 10**1000):
            self.selection, self.count, self.effort = fixture()
            self.effort['rows'][0]['active_search_seconds'] = value
            self.reseal()
            with self.subTest(effort=type(value)), self.assertRaises(ValueError):
                self.call()

    def test_json_invalid_numbers_cycles_and_identity_changes_are_rejected(self):
        self.count['rows'][0]['count'] = True
        self.reseal()
        with self.assertRaises(ValueError):
            self.call()
        self.selection, self.count, self.effort = fixture()
        self.effort['rows'][0]['active_search_seconds'] = float('nan')
        with self.assertRaises(ValueError):
            self.call()
        self.selection, self.count, self.effort = fixture()
        self.count['rows'].append(self.count)
        with self.assertRaises(self.module.CountCapacityBlocked):
            self.call()
        self.selection, self.count, self.effort = fixture()
        self.selection['accepted'][0]['features']['rain_mm'] = 99
        with self.assertRaises(ValueError):
            self.call()

    def test_reserved_paths_unknown_sources_roles_cycles_and_fields_are_invalid(self):
        for kind in ('path', 'id', 'role', 'cycle', 'field'):
            self.selection, self.count, self.effort = fixture()
            node = self.count['source_nodes'][0]
            if kind == 'path':
                node['ref']['path'] = 'evidence/Sealed/confirmation.json'
            elif kind == 'id':
                self.count['rows'][0]['events'][0]['outcome_source_ids'] = ['missing']
            elif kind == 'role':
                node['source_role'] = 'feature'
            elif kind == 'cycle':
                node.update(source_kind='DERIVED', parents=['outcomes'])
            else:
                node['independent'] = True
            self.reseal()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.call()

    def test_missing_registration_needs_data_but_conflicting_known_hash_is_invalid(self):
        path = self.count['source_nodes'][0]['ref']['path']
        self.selection['source_sha256'].pop(path)
        self.selection['source_received_at'].pop(path)
        bind_selection(self.selection)
        for p in (self.count, self.effort):
            p['selection_sha256'] = self.selection['selection_sha256']
        self.reseal()
        self.assertEqual(self.call()['status'], 'NEED_MORE_DATA')
        self.selection, self.count, self.effort = fixture()
        self.count['source_nodes'][0]['ref']['sha256'] = 'f' * 64
        self.reseal()
        with self.assertRaises(ValueError):
            self.call()

    def test_effort_outcome_byte_alias_even_under_different_path_is_invalid(self):
        node = self.effort['source_nodes'][0]
        node['ref']['sha256'] = self.count['source_nodes'][0]['ref']['sha256']
        self.selection['source_sha256'][node['ref']['path']] = node['ref']['sha256']
        bind_selection(self.selection)
        for p in (self.count, self.effort):
            p['selection_sha256'] = self.selection['selection_sha256']
        self.reseal()
        with self.assertRaises(ValueError):
            self.call()

    def test_missing_row_needs_data_but_extra_or_duplicate_rows_are_invalid(self):
        row = self.effort['rows'].pop()
        self.reseal()
        self.assertEqual(self.call()['status'], 'NEED_MORE_DATA')
        self.effort['rows'].append(row)
        self.effort['rows'].append(copy.deepcopy(row))
        self.reseal()
        with self.assertRaises(ValueError):
            self.call()

    def test_bad_provided_projection_is_not_hidden_by_missing_other_projection(self):
        self.count['unexpected'] = True
        seal(self.count)
        with self.assertRaises(ValueError):
            self.module.assess_count_feasibility(self.selection, self.count, None)

    def test_missing_effort_does_not_hide_event_outside_declared_complete_scope(self):
        self.count['rows'][0]['complete_scope']['active_intervals'][0]['start'] = '2026-09-01T20:03:00+09:00'
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'scope'):
            self.module.assess_count_feasibility(self.selection, self.count, None)

    def test_no_files_network_input_mutation_or_forecast_outputs(self):
        before = copy.deepcopy((self.selection, self.count, self.effort))
        with patch('builtins.open', side_effect=AssertionError('file access')), \
             patch.object(Path, 'open', side_effect=AssertionError('file access')), \
             patch.object(socket, 'socket', side_effect=AssertionError('network')):
            result = self.call()
        self.assertEqual((self.selection, self.count, self.effort), before)
        self.assertEqual(result['assessment_sha256'], sha({k: v for k, v in result.items() if k != 'assessment_sha256'}))
        self.assertNotIn('features', result)

    def test_combined_json_capacity_and_lineage_capacity_are_enforced(self):
        for name, maximum in [('MAX_JSON_BYTES', 1000), ('MAX_LINEAGE_MEMBERSHIPS', 3)]:
            with self.subTest(cap=name), patch.object(self.module, name, maximum):
                with self.assertRaises(self.module.CountCapacityBlocked):
                    self.call()

    def test_callback_expiry_during_initial_copy_and_final_seal_returns_nothing(self):
        with self.assertRaises(TimeoutError):
            self.call(check=lambda: (_ for _ in ()).throw(TimeoutError('shared budget')))
        clock = [0.0]
        real = self.module._digest
        def expire(value, check):
            answer = real(value, check)
            if isinstance(value, dict) and 'source_authentication' in value:
                clock[0] = 31.0
            return answer
        with patch.object(self.module, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(self.module, '_digest', side_effect=expire):
            with self.assertRaises(TimeoutError):
                self.call()


if __name__ == '__main__':
    unittest.main()
