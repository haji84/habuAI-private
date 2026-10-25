"""Synthetic records and actual POSIX bare-Git transport; no trusted root claim."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import development_handoff as h
from master_contracts import canonical_bytes, digest

SOURCE = '4'*40
ROOT_ID = '1'*64
NIGHT = '2026-10-25'


def new_ledger():
    return h.new_science_ledger(ROOT_ID, NIGHT, {'uniform':'a'*64, 'HB-A0':'b'*64, 'HB-A1':'c'*64})


def reserve(ledger, source=SOURCE):
    return h.reserve_science(ledger, expected_tip=ledger['tip_sha256'], operation_id='2'*64,
        child_command_id='3'*64, source_commit=source, attempt_id='5'*64, round_id='6'*64,
        recipes=ledger['origin']['preregistered_recipes'], milliseconds=200000,
        now='2026-10-25T08:00:00Z', lease_until='2026-10-25T08:10:00Z')


class PublicationRecordTests(unittest.TestCase):
    def test_transport_import_does_not_load_the_scientific_locking_engine(self):
        script = """import builtins,sys
sys.path.insert(0,sys.argv[1])
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name=='master_orchestrator': raise AssertionError('eager scientific engine import')
    return original(name,*args,**kwargs)
builtins.__import__=guarded
import pdca_bridge
assert callable(pdca_bridge.GitTransport)
try: pdca_bridge.inspect_run_identity(None,None)
except AssertionError as error: assert str(error)=='eager scientific engine import'
else: raise AssertionError('scientific call did not load its actual engine')
"""
        result = subprocess.run([sys.executable,'-B','-X','utf8','-c',script,str(Path(h.__file__).parent)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def records(self, ledger=None):
        method = getattr(h, '_science_publication_records', None)
        self.assertTrue(callable(method), 'fixed publication record builder missing')
        return method(new_ledger() if ledger is None else ledger, SOURCE)

    def test_exact_paths_and_canonical_record_bytes(self):
        branch, prefix, records = self.records()
        self.assertEqual(branch, 'pdca/science-'+ROOT_ID)
        self.assertEqual(prefix, f'reports/pdca/{NIGHT}/bridge/science/{ROOT_ID}/')
        self.assertEqual(set(records), {prefix+'origin.json', prefix+'state.json'})
        for raw in records.values():
            value = json.loads(raw)
            self.assertEqual(raw, canonical_bytes(value)+b'\n')
            self.assertEqual(value['root_report_source_commit'], SOURCE)
            for key in h.FLAGS: self.assertIs(value[key], False)

    def test_semantic_tip_proposal_hash_and_physical_bytes_are_distinct(self):
        ledger = reserve(new_ledger())
        _, prefix, records = self.records(ledger)
        event = ledger['events'][0]
        path = prefix+f"events/0001-{event['event_sha256']}.json"
        self.assertIn(path, records)
        value = json.loads(records[path])
        self.assertEqual(value['event'], event)
        self.assertEqual(value['proposal_sha256'], digest(ledger))
        state = json.loads(records[prefix+'state.json'])
        self.assertEqual(state['proposal'], ledger)
        self.assertEqual(state['proposal_sha256'], digest(ledger))
        self.assertEqual(state['origin_record_sha256'], digest(json.loads(records[prefix+'origin.json'])))

    def test_all_prefix_proposals_are_reconstructed_without_saved_summary_trust(self):
        first = reserve(new_ledger())
        ended = h.settle_science(first, expected_tip=first['tip_sha256'], attempt_id='5'*64,
            generation=1, elapsed_ms=120000, now='2026-10-25T08:01:00Z')
        _, prefix, records = self.records(ended)
        event = first['events'][0]
        self.assertEqual(json.loads(records[prefix+f"events/0001-{event['event_sha256']}.json"])
            ['proposal_sha256'], digest(first))
        self.assertEqual(len(records), 4)

    def test_inputs_are_detached_and_wrong_source_and_authority_reject(self):
        ledger = new_ledger(); before = copy.deepcopy(ledger)
        _, _, records = self.records(ledger)
        ledger['origin']['preregistered_recipes'].clear()
        self.assertTrue(all(type(raw) is bytes for raw in records.values()))
        self.assertEqual(json.loads(next(raw for path,raw in records.items() if path.endswith('/state.json')))['proposal'], before)
        method = getattr(h, '_science_publication_records', None)
        self.assertTrue(callable(method))
        with self.assertRaises(ValueError): method(before, 'not-a-source')
        before['execution_authorized'] = True
        with self.assertRaises(ValueError): method(before, SOURCE)

    def test_metadata_path_limit_precedes_payload_access(self):
        _, prefix, _ = self.records()
        class MetadataOnly:
            def git(self, *args):
                return b'100644 blob '+b'1'*40+b'\t'+(prefix+'x'*513).encode()+b'\0'
            def read(self, *args): raise AssertionError('payload opened for invalid metadata')
        with self.assertRaises(ValueError): h._report_tree(MetadataOnly(), SOURCE, prefix)


class ActualGitPublicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.checkout, self.remote = self.base/'checkout', self.base/'remote.git'
        self.checkout.mkdir()
        self.git('init', '--bare', str(self.remote), root=self.base)
        self.git('init')
        self.git('config', 'user.name', 'Synthetic transport test')
        self.git('config', 'user.email', 'transport@example.invalid')
        (self.checkout/'trusted.txt').write_bytes(b'synthetic trusted source\n')
        self.git('add', 'trusted.txt'); self.git('commit', '-m', 'Synthetic source')
        self.git('branch', '-M', 'main')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-u', 'origin', 'main')
        self.source = self.git('rev-parse', 'HEAD').decode().strip()
        from pdca_bridge import GitTransport
        self.transport = GitTransport(self.checkout)
        self.method = getattr(h, 'publish_science_ledger', None)
        self.assertTrue(callable(self.method), 'fixed public publisher missing')

    def git(self, *args, root=None):
        return subprocess.check_output(['git','-C',str(root or self.checkout),*args], stderr=subprocess.PIPE)

    def publish(self, proposal, head=None, tip=None):
        return self.method(self.checkout, proposal, root_report_source_commit=self.source,
            expected_remote_head=head, expected_tip=tip or proposal['tip_sha256'])

    def bootstrap(self):
        ledger = new_ledger(); receipt = self.publish(ledger)
        return ledger, receipt

    def test_real_bootstrap_append_and_clean_restart(self):
        ledger, boot = self.bootstrap(); child = reserve(ledger)
        done = self.publish(child, boot['observed_head'], ledger['tip_sha256'])
        self.assertEqual(done['latest_proposal'], child)
        self.assertEqual(done['latest_tip'], child['tip_sha256'])
        self.assertGreater(done['actual_blob_bytes_read'], 0)
        for key in h.FLAGS: self.assertIs(done[key], False)
        again = self.publish(child, boot['observed_head'], ledger['tip_sha256'])
        self.assertEqual(again['observed_head'], done['observed_head'])
        self.assertEqual(again['status'], 'TRANSPORT_ACK_ONLY')

    def test_two_real_writers_cannot_spend_one_predecessor_twice(self):
        ledger, boot = self.bootstrap(); first = reserve(ledger)
        second = h.reserve_science(ledger, expected_tip=ledger['tip_sha256'], operation_id='7'*64,
            child_command_id='8'*64, source_commit=self.source, attempt_id='9'*64, round_id='a'*64,
            recipes=ledger['origin']['preregistered_recipes'], milliseconds=200000,
            now='2026-10-25T08:00:00Z', lease_until='2026-10-25T08:10:00Z')
        self.publish(first, boot['observed_head'], ledger['tip_sha256'])
        with self.assertRaises(ValueError): self.publish(second, boot['observed_head'], ledger['tip_sha256'])

    def test_ambiguous_native_push_is_reconciled_and_no_new_commit_created(self):
        ledger, boot = self.bootstrap(); child = reserve(ledger)
        from pdca_bridge import GitTransport
        original = GitTransport.publish
        def after_push(instance, *args, **kwargs):
            original(instance, *args, **kwargs)
            raise OSError('Synthetic lost response after actual native push')
        with patch.object(GitTransport, 'publish', new=after_push):
            receipt = self.publish(child, boot['observed_head'], ledger['tip_sha256'])
        self.assertEqual(receipt['latest_proposal'], child)
        branch = 'pdca/science-'+ROOT_ID
        self.assertEqual(int(self.git('rev-list','--count',f'{self.source}..{self.transport.head(branch)}')), 2)

    def test_prefix_ack_returns_latest_expired_state_never_live_old_reservation(self):
        ledger, boot = self.bootstrap(); child = reserve(ledger)
        claimed = self.publish(child, boot['observed_head'], ledger['tip_sha256'])
        expired = h.expire_science(child, expected_tip=child['tip_sha256'], attempt_id='5'*64,
            generation=1, now='2026-10-25T08:11:00Z')
        ended = self.publish(expired, claimed['observed_head'], child['tip_sha256'])
        again = self.publish(child, boot['observed_head'], ledger['tip_sha256'])
        self.assertEqual(again['observed_head'], ended['observed_head'])
        self.assertEqual(again['latest_proposal'], expired)
        self.assertEqual(h.inspect_science_ledger(again['latest_proposal'])['used_ms'], 200000)
        self.assertIs(again['execution_authorized'], False)

    def test_immutable_whitespace_rewrite_rejects(self):
        ledger, boot = self.bootstrap(); branch = 'pdca/science-'+ROOT_ID
        _, prefix, records = h._science_publication_records(ledger, self.source)
        self.transport.publish(branch, self.source, boot['observed_head'],
            {prefix+'origin.json':records[prefix+'origin.json']+b' '})
        with self.assertRaises(ValueError): self.publish(reserve(ledger), boot['observed_head'], ledger['tip_sha256'])

    def test_foreign_bridge_file_rejects_without_repairing_or_resetting_branch(self):
        ledger, boot = self.bootstrap(); branch = 'pdca/science-'+ROOT_ID
        foreign = f'reports/pdca/{NIGHT}/bridge/foreign.json'
        altered = self.transport.publish(branch, self.source, boot['observed_head'], {foreign:b'{}\n'})
        with self.assertRaises(ValueError): self.publish(reserve(ledger), altered, ledger['tip_sha256'])
        self.assertEqual(self.transport.head(branch), altered)

    def test_blob_cap_is_checked_before_any_oversized_payload_read(self):
        ledger, boot = self.bootstrap(); branch = 'pdca/science-'+ROOT_ID
        _, prefix, _ = h._science_publication_records(ledger, self.source)
        self.transport.publish(branch, self.source, boot['observed_head'],
            {prefix+'state.json':b'x'*(h.MAX_REPORT_BLOB_BYTES+1)})
        from pdca_bridge import GitTransport
        native = GitTransport.read
        def checked(instance, commit, path):
            if path == prefix+'state.json': raise AssertionError('oversized payload materialized')
            return native(instance, commit, path)
        with patch.object(GitTransport,'read',new=checked), self.assertRaises(ValueError):
            self.publish(reserve(ledger), boot['observed_head'], ledger['tip_sha256'])

    def test_new_scientific_source_does_not_advance_report_base(self):
        ledger, boot = self.bootstrap()
        (self.checkout/'next-code.txt').write_bytes(b'synthetic next code version\n')
        self.git('add','.'); self.git('commit','-m','Synthetic source update'); self.git('push','origin','main')
        newer = self.git('rev-parse','HEAD').decode().strip()
        child = reserve(ledger, source=newer)
        receipt = self.publish(child, boot['observed_head'], ledger['tip_sha256'])
        self.assertEqual(receipt['root_report_source_commit'], self.source)
        self.assertEqual(receipt['latest_proposal']['events'][0]['source_commit'], newer)

    def test_real_sibling_push_race_preserves_the_first_remote_winner(self):
        ledger, boot = self.bootstrap(); first = reserve(ledger)
        other = h.reserve_science(ledger, expected_tip=ledger['tip_sha256'], operation_id='7'*64,
            child_command_id='8'*64, source_commit=self.source, attempt_id='9'*64, round_id='a'*64,
            recipes=ledger['origin']['preregistered_recipes'], milliseconds=200000,
            now='2026-10-25T08:00:00Z', lease_until='2026-10-25T08:10:00Z')
        from pdca_bridge import GitTransport
        native = GitTransport.git
        winner, injected = [], []
        def interleave(instance, *args, **kwargs):
            if args[0] == 'push' and not injected:
                injected.append(True)
                winner.append(self.publish(other, boot['observed_head'], ledger['tip_sha256']))
            return native(instance, *args, **kwargs)
        with patch.object(GitTransport,'git',new=interleave), self.assertRaises(ValueError):
            self.publish(first, boot['observed_head'], ledger['tip_sha256'])
        self.assertEqual(injected, [True])
        self.assertEqual(self.transport.head('pdca/science-'+ROOT_ID), winner[0]['observed_head'])
        self.assertEqual(winner[0]['latest_proposal'], other)

    def test_preexisting_base_namespace_cannot_be_bootstrapped_at_zero(self):
        ledger = new_ledger()
        _, prefix, records = h._science_publication_records(ledger, self.source)
        path = self.checkout/prefix/'origin.json'; path.parent.mkdir(parents=True)
        path.write_bytes(records[prefix+'origin.json'])
        self.git('add', '.'); self.git('commit', '-m', 'Synthetic existing campaign evidence')
        self.source = self.git('rev-parse','HEAD').decode().strip()
        self.git('push','origin','main')
        with self.assertRaises(ValueError): self.publish(ledger)


if __name__ == '__main__': unittest.main()
