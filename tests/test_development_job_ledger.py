"""Synthetic engineering accounting, not authorized jobs or real runtime proof."""
import copy
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'), str(Path(__file__).resolve().parent)]
import development_handoff as contracts
from test_development_handoff import development_provenance, development_need
try:
    import development_job_ledger as jobs
except ModuleNotFoundError as exc:
    if exc.name != 'development_job_ledger':
        raise
    jobs = None


def clock(seconds=0):
    return (datetime.fromisoformat('2026-10-25T08:00:00+00:00')+timedelta(seconds=seconds)).isoformat()


def request(**changes):
    context = development_provenance()
    context.update(changes)
    if 'operational_night' in changes or 'parent_run_id' in changes:
        context['evidence'][0]['path'] = (f"reports/pdca/{context['operational_night']}/runs/"
            f"{context['parent_run_id']}/stages/development.json")
    return contracts.propose_development_request(context,development_need())['request']


class DevelopmentJobLedgerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(jobs, 'bounded development job ledger API missing')
        self.origin = jobs.new_development_job(request())

    def apply(self, ledger, kind, **fields):
        return jobs.append_development_job(ledger, expected_tip=ledger['tip_sha256'],
            transition=dict(kind=kind, **fields))

    def start(self, ledger=None, **changes):
        fields = dict(request=request(), now=clock(), lease_until=clock(600))
        fields.update(changes)
        return self.apply(self.origin if ledger is None else ledger, 'START', **fields)

    def info(self, ledger):
        return jobs.inspect_development_job(ledger)

    def current(self, ledger):
        return self.info(ledger)['attempts'][-1]

    def checkpoint(self, ledger, active_ms=1000, phase='ACTIVE', **changes):
        attempt = self.current(ledger)
        fields = dict(attempt_id=attempt['attempt_id'],generation=attempt['generation'],
            active_ms=active_ms,phase=phase,now=clock(10),
            lease_until=clock(610) if phase == 'ACTIVE' else None)
        fields.update(changes)
        return self.apply(ledger,'CHECKPOINT',**fields)

    def settle(self, ledger, active_ms=1000, **changes):
        attempt = self.current(ledger)
        fields = dict(attempt_id=attempt['attempt_id'],generation=attempt['generation'],
            active_ms=active_ms,now=clock(20))
        fields.update(changes)
        return self.apply(ledger,'SETTLE',**fields)

    def test_origin_and_proposals_have_no_authority_or_saved_totals(self):
        info = self.info(self.origin)
        self.assertEqual(info['used_ms'],0)
        self.assertEqual(info['reserved_ms'],0)
        self.assertEqual(info['remaining_ms'],7200000)
        self.assertEqual(self.origin['persistence'],'UNPUBLISHED_ACCOUNTING_PROPOSAL')
        for value in (self.origin,info):
            for field in ('request_admitted','execution_authorized','scientific_authorized',
                          'selection_authorized','production_authorized','github_facts_authenticated'):
                self.assertIs(value[field],False)
        forged = copy.deepcopy(self.origin); forged['used_ms'] = 0
        with self.assertRaises(ValueError): self.info(forged)

    def test_start_respects_declared_request_window_without_actual_clock_attestation(self):
        for instant in (clock(-1),clock(86400)):
            with self.subTest(now=instant),self.assertRaises(ValueError):
                self.start(now=instant,lease_until=(datetime.fromisoformat(instant)+timedelta(seconds=600)).isoformat())

    def test_stable_root_capability_job_and_second_changed_source_request_share_two_attempts(self):
        other = request(source_commit='a'*40, parent_run_id='b'*64, operational_night='2026-10-26')
        self.assertEqual(self.origin['origin']['job_id'],jobs.new_development_job(other)['origin']['job_id'])
        first = self.settle(self.start(),active_ms=3600000)
        second = self.start(first,request=other,now=clock(30),lease_until=clock(630))
        info = self.info(second)
        self.assertEqual(info['used_ms'],3600000)
        self.assertEqual(info['reserved_ms'],3600000)
        self.assertEqual(info['remaining_ms'],0)
        self.assertEqual(info['attempts'][1]['source_commit'],'a'*40)
        second = self.settle(second,active_ms=3600000,now=clock(40))
        with self.assertRaises(ValueError): self.start(second,now=clock(50),lease_until=clock(650))

    def test_long_ci_wait_fences_old_worker_and_resumes_same_attempt_without_wait_charge(self):
        active = self.start(); old = self.current(active)
        paused = self.checkpoint(active,active_ms=1234,phase='WAITING_CI')
        info = self.info(paused)
        self.assertEqual(info['used_ms'],1234)
        self.assertIsNone(self.current(paused)['lease_until'])
        self.assertNotEqual(old['generation'],self.current(paused)['generation'])
        with self.assertRaises(ValueError): self.settle(paused,generation=old['generation'])
        with self.assertRaises(ValueError): self.settle(paused,active_ms=1235,now=clock(7000))
        resumed = self.checkpoint(paused,active_ms=1234,now=clock(7200),lease_until=clock(7800))
        self.assertEqual(self.current(resumed)['attempt_id'],old['attempt_id'])
        self.assertEqual(self.current(resumed)['ordinal'],1)
        done = self.settle(resumed,active_ms=2234,now=clock(7210))
        self.assertEqual(self.info(done)['used_ms'],2234)
        self.assertEqual(self.info(done)['reserved_ms'],0)

    def test_expiry_equality_charges_full_allowance_and_stale_completion_cannot_refund(self):
        active = self.start(); attempt = self.current(active)
        for call in (lambda:self.checkpoint(active,now=clock(600),lease_until=clock(1200)),
                     lambda:self.settle(active,now=clock(600))):
            with self.assertRaises(ValueError): call()
        expired = self.apply(active,'EXPIRE',attempt_id=attempt['attempt_id'],
            generation=attempt['generation'],now=clock(600))
        self.assertEqual(self.info(expired)['used_ms'],3600000)
        self.assertEqual(self.info(expired)['reserved_ms'],0)
        with self.assertRaises(ValueError): self.settle(expired,active_ms=1000,now=clock(601))
        paused = self.checkpoint(self.start(),phase='WAITING_CI')
        with self.assertRaises(ValueError): self.apply(paused,'EXPIRE',attempt_id=attempt['attempt_id'],
            generation=self.current(paused)['generation'],now=clock(7000))

    def test_overrun_records_full_actual_and_stops_whole_job(self):
        over = self.settle(self.start(),active_ms=3600001)
        self.assertEqual(self.info(over)['used_ms'],3600001)
        self.assertEqual(self.info(over)['remaining_ms'],0)
        self.assertIs(self.info(over)['budget_exceeded'],True)
        with self.assertRaises(ValueError): self.start(over,now=clock(30),lease_until=clock(630))
        with self.assertRaisesRegex(ValueError,'CAPACITY_BLOCKED'):
            self.settle(self.start(),active_ms=86400001)

    def test_late_overrun_after_expiry_adds_only_positive_delta_without_worker_revival(self):
        active = self.start(); attempt = self.current(active)
        expired = self.apply(active,'EXPIRE',attempt_id=attempt['attempt_id'],
            generation=attempt['generation'],now=clock(600))
        incident = self.settle(expired,generation=attempt['generation'],active_ms=4000000,now=clock(1000))
        self.assertEqual(self.info(incident)['used_ms'],4000000)
        self.assertEqual(self.info(incident)['reserved_ms'],0)
        more = self.settle(incident,generation=attempt['generation'],active_ms=4100000,now=clock(1001))
        self.assertEqual(self.info(more)['used_ms'],4100000)
        with self.assertRaises(ValueError): self.settle(more,active_ms=4050000,now=clock(1002))

    def test_waiting_and_closed_fence_generations_cannot_invent_active_overrun(self):
        active = self.start(); original = self.current(active)
        paused = self.checkpoint(active,active_ms=1000,phase='WAITING_CI')
        settled = self.settle(active,active_ms=1000)
        for ledger in (paused,settled):
            with self.subTest(phase=self.current(ledger)['phase']),self.assertRaises(ValueError):
                self.settle(ledger,active_ms=3600001,now=clock(7000))
        incident = self.settle(paused,generation=original['generation'],active_ms=3600001,now=clock(7000))
        self.assertEqual(self.info(incident)['used_ms'],3600001)

    def test_late_first_overrun_fences_and_conservatively_charges_other_active_attempt(self):
        first = self.start(); old = self.current(first)
        first = self.settle(first,active_ms=1000)
        second = self.start(first,now=clock(30),lease_until=clock(630))
        incident = self.settle(second,attempt_id=old['attempt_id'],generation=old['generation'],
            active_ms=4000000,now=clock(40))
        self.assertEqual(self.info(incident)['used_ms'],7600000)
        self.assertEqual(self.info(incident)['reserved_ms'],0)
        self.assertEqual(self.info(incident)['remaining_ms'],0)
        with self.assertRaises(ValueError): self.settle(incident,active_ms=1000,now=clock(50))

    def test_late_overrun_does_not_charge_reserved_ci_wait_as_active_work(self):
        first = self.start(); old = self.current(first)
        first = self.settle(first,active_ms=1000)
        second = self.start(first,now=clock(30),lease_until=clock(630))
        paused = self.checkpoint(second,phase='WAITING_CI',active_ms=1234,now=clock(40))
        incident = self.settle(paused,attempt_id=old['attempt_id'],generation=old['generation'],
            active_ms=4000000,now=clock(50))
        self.assertEqual(self.info(incident)['used_ms'],4001234)
        self.assertEqual(self.info(incident)['reserved_ms'],0)

    def test_extreme_declared_year_lease_difference_does_not_overflow(self):
        req = request(observed_at='9999-12-31T00:00:00+00:00',expires_at='9999-12-31T01:00:00+00:00')
        active = self.start(request=req,now='9999-12-31T00:00:00+00:00',
            lease_until='9999-12-31T00:10:00+00:00')
        self.assertEqual(self.info(active)['reserved_ms'],3600000)

    def test_schema_and_strict_boolean_proposal_flags(self):
        import json
        schema = json.loads((Path(__file__).resolve().parents[1]/'schemas/development-job-ledger.json').read_bytes())
        self.assertEqual(set(schema['required']),set(self.origin))
        for field in ('execution_authorized','request_admitted','github_facts_authenticated'):
            forged = copy.deepcopy(self.origin); forged[field] = 0
            with self.subTest(field=field),self.assertRaises(ValueError): self.info(forged)

    def test_current_tip_exact_settlement_retry_is_idempotent_and_stale_tip_rejects(self):
        active = self.start(); attempt = self.current(active)
        done = self.settle(active)
        transition = dict(kind='SETTLE',attempt_id=attempt['attempt_id'],
            generation=attempt['generation'],active_ms=1000,now=clock(20))
        self.assertEqual(jobs.append_development_job(done,expected_tip=done['tip_sha256'],transition=transition),done)
        with self.assertRaises(ValueError): jobs.append_development_job(done,
            expected_tip=active['tip_sha256'],transition=transition)
        with self.assertRaises(ValueError): self.settle(done,active_ms=1001,now=clock(21))

    def test_known_types_scope_source_clock_and_unknown_command_fields_reject(self):
        for field,value in [('active_ms',True),('generation',True),('active_ms',-1),
                            ('command','shell'),('now',clock(-1)),('attempt_id','f'*64)]:
            active = self.start()
            with self.subTest(field=field),self.assertRaises(ValueError): self.settle(active,**{field:value})
        active = self.start()
        for change in (dict(request=request()),dict(lease_until=clock(611)),dict(phase='OTHER')):
            with self.subTest(change=change),self.assertRaises(ValueError): self.checkpoint(active,**change)
        foreign = request(root_command_id='f'*64)
        with self.assertRaises(ValueError): self.start(request=foreign)

    def test_hash_chain_derived_attempts_and_saved_origin_limits_cannot_be_rehashed_away(self):
        active = self.start()
        for field,value in [('ordinal',2),('allowance_ms',1),('attempt_id','f'*64)]:
            forged = copy.deepcopy(active); forged['events'][0][field] = value
            event = forged['events'][0]
            event['event_sha256'] = contracts.digest({k:v for k,v in event.items() if k != 'event_sha256'})
            forged['tip_sha256'] = event['event_sha256']
            with self.subTest(field=field),self.assertRaises(ValueError): self.info(forged)
        forged = copy.deepcopy(self.origin); forged['origin']['limits']['attempts'] = 3
        forged['tip_sha256'] = contracts.digest(forged['origin'])
        with self.assertRaises(ValueError): self.info(forged)

    def test_detached_bounded_no_io_and_capacity_does_not_reset_history(self):
        from unittest.mock import patch
        import socket
        with patch('builtins.open',side_effect=AssertionError('file')), \
                patch.object(socket,'socket',side_effect=AssertionError('network')):
            active = self.start(); saved = copy.deepcopy(active)
            summary = self.info(active); summary['attempts'][0]['source_commit'] = 'f'*40
        self.assertEqual(active,saved)
        with patch.object(jobs,'MAX_EVENTS',1),self.assertRaisesRegex(ValueError,'CAPACITY_BLOCKED'):
            self.checkpoint(active)
        self.assertEqual(active,saved)


if __name__ == '__main__':
    unittest.main()
