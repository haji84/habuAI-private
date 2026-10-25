"""Synthetic accounting contracts; no authenticated controller execution."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import development_handoff as h

NOW = '2026-10-25T08:00:00+00:00'
LATER = '2026-10-25T08:10:00+00:00'
RECIPES = {'uniform': 'a'*64, 'HB-A0': 'b'*64, 'HB-A1': 'c'*64}


def origin():
    return h.new_science_ledger('1'*64, '2026-10-25', RECIPES)


def reserve(ledger, **changes):
    args = dict(expected_tip=ledger['tip_sha256'], operation_id='2'*64,
        child_command_id='3'*64, source_commit='4'*40, attempt_id='5'*64,
        round_id='6'*64, recipes=RECIPES, milliseconds=200000,
        now=NOW, lease_until=LATER)
    args.update(changes)
    return h.reserve_science(ledger, **args)


class ScienceRootLedgerTests(unittest.TestCase):
    def test_origin_and_every_proposal_have_no_execution_authority(self):
        ledger = origin()
        self.assertEqual(h.inspect_science_ledger(ledger)['remaining_ms'], 300000)
        result = reserve(ledger)
        for key in ('execution_authorized', 'scientific_authorized', 'selection_authorized', 'production_authorized'):
            self.assertIs(result[key], False)
        self.assertEqual(result['persistence'], 'UNPUBLISHED_PROPOSAL')

    def test_reserve_then_settle_parent200s_child_gets_only100s(self):
        first = reserve(origin())
        settled = h.settle_science(first, expected_tip=first['tip_sha256'], attempt_id='5'*64,
            generation=1, elapsed_ms=200000, now=NOW)
        self.assertEqual(h.inspect_science_ledger(settled)['remaining_ms'], 100000)
        second = reserve(settled, operation_id='7'*64, child_command_id='8'*64,
            source_commit='9'*40, attempt_id='a'*64, round_id='b'*64, milliseconds=100000)
        self.assertEqual(h.inspect_science_ledger(second)['remaining_ms'], 0)
        with self.assertRaises(ValueError):
            reserve(settled, operation_id='7'*64, attempt_id='a'*64, round_id='b'*64, milliseconds=100001)

    def test_reserved_compute_and_round_cannot_be_double_spent(self):
        first = reserve(origin())
        with self.assertRaises(ValueError): reserve(first, attempt_id='a'*64)
        with self.assertRaises(ValueError): reserve(first, operation_id='7'*64,
            child_command_id='8'*64, attempt_id='a'*64, round_id='b'*64, milliseconds=100001)

    def test_stale_tip_and_two_writer_proposals_are_distinct_no_atomicity_claim(self):
        base = origin(); first = reserve(base)
        other = reserve(base, operation_id='7'*64, child_command_id='8'*64, attempt_id='a'*64)
        self.assertNotEqual(first['tip_sha256'], other['tip_sha256'])
        self.assertEqual(first['events'][0]['previous_sha256'], base['tip_sha256'])
        with self.assertRaises(ValueError): reserve(first, expected_tip=base['tip_sha256'], attempt_id='a'*64)

    def test_expired_lease_charges_full_reservation_and_fences_late_settlement(self):
        first = reserve(origin())
        late = '2026-10-25T08:10:00.001+00:00'
        expired = h.expire_science(first, expected_tip=first['tip_sha256'], attempt_id='5'*64,
            generation=1, now=late)
        info = h.inspect_science_ledger(expired)
        self.assertEqual(info['used_ms'], 200000)
        self.assertEqual(info['remaining_ms'], 100000)
        with self.assertRaises(ValueError): h.settle_science(expired, expected_tip=expired['tip_sha256'],
            attempt_id='5'*64, generation=1, elapsed_ms=1, now=late)

    def test_settlement_idempotency_and_mismatch(self):
        first = reserve(origin())
        kwargs = dict(attempt_id='5'*64, generation=1, elapsed_ms=120000, now=NOW)
        settled = h.settle_science(first, expected_tip=first['tip_sha256'], **kwargs)
        self.assertEqual(h.settle_science(settled, expected_tip=settled['tip_sha256'], **kwargs), settled)
        with self.assertRaises(ValueError): h.settle_science(settled, expected_tip=settled['tip_sha256'], **dict(kwargs, elapsed_ms=119999))
        self.assertEqual(h.inspect_science_ledger(settled)['remaining_ms'], 180000)

    def test_third_round_and_unregistered_or_changed_recipe_reject(self):
        ledger = origin()
        for index in (1, 2):
            digit = str(index)
            ledger = reserve(ledger, operation_id=digit*64, child_command_id=digit*64,
                attempt_id=digit*64, round_id=digit*64, milliseconds=1)
            ledger = h.settle_science(ledger, expected_tip=ledger['tip_sha256'], attempt_id=digit*64,
                generation=len(ledger['events']), elapsed_ms=1, now=NOW)
        with self.assertRaises(ValueError): reserve(ledger, attempt_id='f'*64, round_id='f'*64, milliseconds=1)
        for recipes in (dict(RECIPES, **{'HB-B1': 'd'*64}), dict(RECIPES, **{'HB-A1':'e'*64})):
            with self.assertRaises(ValueError): reserve(origin(), recipes=recipes)

    def test_canonical_operation_child_source_cannot_change_after_settlement(self):
        first = reserve(origin())
        settled = h.settle_science(first, expected_tip=first['tip_sha256'], attempt_id='5'*64,
            generation=1, elapsed_ms=1, now=NOW)
        for changes in ({'child_command_id':'d'*64}, {'source_commit':'e'*40}):
            with self.assertRaises(ValueError): reserve(settled, attempt_id='f'*64, milliseconds=1, **changes)

    def test_invalid_types_timestamps_and_unknown_execution_fields_reject(self):
        for value in (True, 0, -1, 300001, 1.5, float('nan')):
            with self.assertRaises(ValueError): reserve(origin(), milliseconds=value)
        for changes in ({'now':'2026-10-25T08:00:00'}, {'lease_until':NOW}, {'lease_until':'2026-10-25T07:59:00Z'},
                        {'expected_tip':'0'*64}, {'source_commit':'4'*64}, {'recipes':{'uniform':'f'*64}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): reserve(origin(), **changes)
        ledger = origin(); ledger['trusted'] = True
        with self.assertRaises(ValueError): reserve(ledger)

    def test_origin_requires_three_slots_reservation_can_use_frozen_subset(self):
        with self.assertRaises(ValueError): h.new_science_ledger('1'*64, '2026-10-25', {'uniform':'a'*64})
        one = reserve(origin(), recipes={'uniform':'a'*64})
        self.assertEqual(one['events'][0]['recipes'], {'uniform':'a'*64})

    def test_event_history_and_summary_cannot_be_forged(self):
        first = reserve(origin())
        for change in ('history', 'tip', 'summary'):
            bad = copy.deepcopy(first)
            if change == 'history': bad['events'][0]['milliseconds'] = 1
            elif change == 'tip': bad['tip_sha256'] = '0'*64
            else: bad['used_ms'] = 0
            with self.assertRaises(ValueError): h.inspect_science_ledger(bad)

    def test_output_and_inputs_are_detached(self):
        ledger = origin(); before = copy.deepcopy(ledger)
        recipes = copy.deepcopy(RECIPES)
        first = reserve(ledger, recipes=recipes)
        recipes.clear(); first['events'][0]['recipes'].clear()
        self.assertEqual(ledger, before)
        self.assertEqual(h.inspect_science_ledger(ledger)['remaining_ms'], 300000)

    def test_lease_generation_time_and_overrun_reject_without_releasing_allowance(self):
        first = reserve(origin())
        for changes in ({'generation':2}, {'elapsed_ms':200001}, {'elapsed_ms':True},
                        {'now':'2026-10-25T07:59:59Z'}, {'now':'2026-10-25T08:10:00.001Z'}):
            args = dict(expected_tip=first['tip_sha256'], attempt_id='5'*64, generation=1,
                elapsed_ms=1, now=NOW)
            args.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): h.settle_science(first, **args)
        self.assertEqual(h.inspect_science_ledger(first)['reserved_ms'], 200000)
        with self.assertRaises(ValueError): reserve(origin(), lease_until='2026-10-25T08:10:00.001Z')
        with self.assertRaises(ValueError): h.expire_science(first, expected_tip=first['tip_sha256'],
            attempt_id='5'*64, generation=1, now=LATER)

    def test_retry_cannot_reset_same_operation_attempt_limit_or_consumed_round(self):
        ledger = origin()
        for index in range(2):
            ident = str(index+1)*64
            ledger = reserve(ledger, attempt_id=ident, milliseconds=1)
            generation = len(ledger['events'])
            ledger = h.settle_science(ledger, expected_tip=ledger['tip_sha256'], attempt_id=ident,
                generation=generation, elapsed_ms=1, now=NOW)
        self.assertEqual(len(h.inspect_science_ledger(ledger)['rounds']), 1)
        with self.assertRaises(ValueError): reserve(ledger, attempt_id='f'*64, milliseconds=1)
        with self.assertRaises(ValueError): reserve(ledger, attempt_id='f'*64, operation_id='d'*64,
            child_command_id='e'*64, milliseconds=1)

    def test_rehashed_invalid_history_still_fails_semantic_replay(self):
        from master_contracts import digest
        first = reserve(origin())
        first['events'][0]['milliseconds'] = 300001
        event = first['events'][0]
        event['event_sha256'] = digest({k:v for k,v in event.items() if k!='event_sha256'})
        first['tip_sha256'] = event['event_sha256']
        with self.assertRaises(ValueError): h.inspect_science_ledger(first)

    def test_capacity_and_cycles_block_before_owned_parse(self):
        from unittest.mock import patch
        for name in ('MAX_BYTES', 'MAX_NODES'):
            ledger = origin()
            with self.subTest(name=name), patch.object(h, name, 1), \
                    patch.object(h.json, 'loads', side_effect=AssertionError('parse before capacity')), \
                    self.assertRaises(ValueError): h.inspect_science_ledger(ledger)
        ledger = origin(); ledger['events'].append(ledger)
        with self.assertRaises(ValueError): h.inspect_science_ledger(ledger)

    def test_no_io_and_foreign_authority_or_limit_flags(self):
        from unittest.mock import patch
        import socket
        with patch('builtins.open', side_effect=AssertionError('file I/O')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network I/O')):
            self.assertEqual(h.inspect_science_ledger(reserve(origin()))['reserved_ms'], 200000)
        for change in ('repository', 'master_issue', 'limits', 'authority'):
            ledger = origin()
            if change == 'limits': ledger['origin']['limits']['rounds'] = 3
            elif change == 'authority': ledger['execution_authorized'] = True
            else: ledger['origin'][change] = 'foreign'
            with self.subTest(change=change), self.assertRaises(ValueError): h.inspect_science_ledger(ledger)


if __name__ == '__main__':
    unittest.main()
