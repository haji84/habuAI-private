"""Reproduce the preserved five-event cohort without network access or Raw edits."""
import base64
from copy import deepcopy
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from master_contracts import canonical_bytes
from master_inventory import local_path

PROFILE = 'sept28-owner-capture-crosswalk-v1'
REVIEW_PATH = 'evidence/source_reviews/2026-09-28-positive-source-review.json'
CAPTURE = 'data/processed/capture_events/2026/2026-09-28.csv'
RAW = 'data/raw/habu_logs/2026/2026-09-28.json'
INDIVIDUALS = 'data/processed/individuals/2026/2026-09-28.csv'
GPX_DIR = 'data/raw/gpx_archives/2026-09-28-探索.gpx.lines'
CAPSULE = ('evidence/source_reviews/capsules/'
           'ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee'
           '__september-validation.zip.b64')
RECEIPT = 'evidence/source_reviews/2026-09-28-source-capsule-receipt.json'
NOW = '2026-10-25T12:00:00+00:00'


def native(path):
    # Windows autocrlf checkout bytes are deliberately not "repaired". Read the
    # committed original Git blob into an independent native-byte temp snapshot.
    return subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT)


def write(root, path, raw):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def snapshot(root):
    for path in [RAW, CAPTURE, INDIVIDUALS, GPX_DIR + '/manifest.json'] + [
            GPX_DIR + '/part_%03d.txt' % i for i in range(24)]:
        write(root, path, native(path))
    for path in [CAPSULE, RECEIPT, REVIEW_PATH]:
        # The encoded capsule is multiline too; future Windows checkouts must
        # exercise its saved Git bytes rather than an autocrlf representation.
        if subprocess.run(['git','cat-file','-e','HEAD:'+path],cwd=ROOT,capture_output=True).returncode==0:
            raw=native(path)
        else:raw=(ROOT/path).read_bytes()
        write(root,path,raw)


class Reader:
    def __init__(self, root):
        self.root = root
        self.paths = []
        self.bytes = 0
        self.points = 0
        self.ticks = 0
        self.fail_after = None

    def tick(self):
        self.ticks += 1
        if self.fail_after is not None and self.ticks >= self.fail_after:
            raise TimeoutError('shared deadline exhausted')

    def read(self, ref):
        self.tick()
        path = local_path(self.root, ref['path'])
        with path.open('rb') as handle:
            raw = handle.read(ref['size_bytes'] + 1)
        self.bytes += len(raw)
        self.paths.append(ref['path'])
        self.tick()
        return raw

    def point(self):
        self.points += 1
        self.tick()


class Sept28SourceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.find_spec('sept28_positive_source_review')
        cls.module = None if spec is None else __import__('sept28_positive_source_review')

    def setUp(self):
        if self.module is None:
            self.fail('The bounded September 28 source crosswalk verifier is not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        snapshot(self.root)
        self.review = json.loads((self.root / REVIEW_PATH).read_bytes())
        self.reader = Reader(self.root)

    def verify(self, review=None):
        return self.module.verify_review(
            self.review if review is None else review, read_ref=self.reader.read,
            tick=self.reader.tick, consume_point=self.reader.point, now=NOW)

    def payloads(self):
        encoded = (self.root / CAPSULE).read_bytes()
        archive = zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded)))
        member = next(n for n in archive.namelist() if n.endswith('.txt'))
        gpx = b'\n'.join((self.root / (GPX_DIR + '/part_%03d.txt' % i)).read_bytes()
                         for i in range(24))
        return dict(native_log=archive.read(member), raw_log=(self.root / RAW).read_bytes(),
                    captures=(self.root / CAPTURE).read_bytes(),
                    individuals=(self.root / INDIVIDUALS).read_bytes(), gpx=gpx)

    def cross_bind(self, payloads):
        return self.module.cross_bind(**payloads, tick=self.reader.tick,
                                      consume_point=self.reader.point)

    def test_actual_five_events_six_occurrences_reproduce_without_incoming_or_network(self):
        result = self.verify()
        self.assertEqual((result['event_count'], result['individual_count']), (5, 6))
        self.assertEqual([x['count'] for x in result['crosswalk']], [1, 1, 2, 1, 1])
        self.assertEqual([x['source_line'] for x in result['crosswalk']],
                         [7712, 7935, 8105, 8115, 8125])
        self.assertEqual(result['gpx_qc']['point_count'], 22990)
        self.assertEqual(result['gpx_qc']['excluded_points'], 0)
        self.assertEqual(result['gpx_qc']['segment_breaks'], 0)
        self.assertAlmostEqual(result['gpx_qc']['maximum_gap_seconds'], 24.401, places=3)
        self.assertEqual(self.reader.points, 22990)
        self.assertTrue(all(not p.startswith('incoming/') for p in self.reader.paths))
        # Each consumed source is reread through the same shared reader.
        self.assertTrue(all(self.reader.paths.count(p) >= 2 for p in set(self.reader.paths)))
        self.assertFalse(result['negative_eligibility_assigned'])
        self.assertFalse(result['training_authorized'])

    def test_changed_source_byte_is_rejected_before_any_capture_qualification(self):
        with (self.root / CAPTURE).open('ab') as handle:
            handle.write(b'\n')
        with self.assertRaises(ValueError):
            self.verify()

    def test_rehashed_metadata_cannot_change_fixed_profile_source(self):
        review = deepcopy(self.review)
        review['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.verify(review)

    def test_tampered_declared_point_or_crosswalk_is_rejected(self):
        for key, value in [('count', 1), ('gpx_sequence', 1), ('source_line', 1)]:
            review = deepcopy(self.review)
            review['proof']['crosswalk'][2][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(review)

    def test_typed_proof_numbers_and_malformed_refs_cannot_bypass_binding(self):
        for key,value in [('count',True),('csv_row',2.0)]:
            review=deepcopy(self.review)
            review['proof']['crosswalk'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.verify(review)
        for value in [None,True,[],1]:
            for key in ['raw_log','gpx_parts']:
                review=deepcopy(self.review)
                if key=='gpx_parts':review['source_refs'][key][0]=value
                else:review['source_refs'][key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    self.verify(review)

    def test_authority_and_historical_review_cannot_be_claimed(self):
        for key in ['negative_eligibility_assigned', 'search_scope_certified',
                    'complete_outcome_coverage_claimed', 'training_authorized',
                    'confirmation_authorized', 'official_issuance_authorized',
                    'production_authorized']:
            review = deepcopy(self.review)
            review[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(review)
        review = deepcopy(self.review)
        review['reviewed_at'] = '2026-09-28T00:00:00Z'
        with self.assertRaises(ValueError):
            self.verify(review)

    def test_review_cannot_claim_independent_device_authentication(self):
        review=deepcopy(self.review)
        review['independent_device_authentication']='ESTABLISHED'
        with self.assertRaises(ValueError):self.verify(review)

    def test_parent_deadline_is_not_reset_or_swallowed(self):
        self.reader.fail_after = 8
        with self.assertRaises(TimeoutError):
            self.verify()

    def test_strict_duplicate_json_at_any_depth(self):
        for raw in [b'{"a":1,"a":2}', b'{"outer":{"a":1,"a":2}}', b'{"a":NaN}',
                    b'{"outer":{"a":1e999}}',b'{"outer":{"a":-1e999}}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.module.strict_json(raw, self.reader.tick)

    def test_source_selector_count_coordinate_and_link_mismatches_reject(self):
        payloads = self.payloads()
        mutations = []
        raw = json.loads(payloads['raw_log'])
        raw['events'][0]['individual_count'] = True
        mutations.append(('raw_log', canonical_bytes(raw)))
        mutations.append(('native_log', payloads['native_log'].replace(
            '畑 枯れ木 2匹'.encode(), '畑 枯れ木 1匹'.encode())))
        mutations.append(('native_log', payloads['native_log'].replace(
            'ハブ捕獲170~180メス'.encode(), 'ヒメハブ捕獲170~180メス'.encode())))
        lines = payloads['captures'].decode('utf-8-sig').splitlines()
        mutations.append(('captures', ('\n'.join(lines + [lines[1]]) + '\n').encode()))
        rows = list(csv.DictReader(io.StringIO(payloads['captures'].decode('utf-8-sig'))))
        rows[0]['latitude'] = 'NaN'
        out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
        mutations.append(('captures', out.getvalue().encode()))
        ilines = payloads['individuals'].decode('utf-8-sig').splitlines()
        mutations.append(('individuals', ('\n'.join(ilines[:-1]) + '\n').encode()))
        mutations.append(('individuals', ('\n'.join(ilines + [ilines[1]]) + '\n').encode()))
        for key, value in mutations:
            changed = dict(payloads); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.cross_bind(changed)

    def test_final_rescan_detects_source_change_after_initial_read(self):
        original = self.reader.read
        def changed(ref):
            raw = original(ref)
            if ref['path'] == CAPTURE and self.reader.paths.count(CAPTURE) == 1:
                (self.root / CAPTURE).write_bytes(raw + b'\n')
            return raw
        self.reader.read = changed
        with self.assertRaises(ValueError):
            self.verify()

    @unittest.skipUnless(os.name != 'nt', 'POSIX symlink test; Windows junction exercised separately')
    def test_capsule_symlink_rejected_before_external_read(self):
        target = self.root / CAPSULE
        outside = self.root.parent / (self.root.name + '-outside')
        outside.write_bytes(target.read_bytes()); self.addCleanup(outside.unlink)
        target.unlink(); target.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.verify()

    def declaration(self, *, profile=PROFILE, duplicate_json=False):
        from evidence_audit import Audit, _declarations
        review = deepcopy(self.review)
        review['use_roles'] = ['outcome_label']
        if profile is None:
            review.pop('verification_profile')
        else:
            review['verification_profile'] = profile
        raw = canonical_bytes(review)
        if duplicate_json:
            raw = raw[:-1] + b',"verification_profile":"' + PROFILE.encode() + b'"}'
        write(self.root, REVIEW_PATH, raw)
        ref = dict(path=REVIEW_PATH, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        policy = dict(schema_version='1.0', sources=[dict(self.review['source_refs']['captures'], review_ref=ref)], sessions=[])
        write(self.root, 'policies/observation_evidence.json', canonical_bytes(policy))
        audit = Audit(self.root, NOW)
        _declarations(audit)
        return audit

    def test_fixed_csv_missing_or_unknown_profile_cannot_use_legacy_role_grant(self):
        for profile in [None, 'unknown-review-v100']:
            with self.subTest(profile=profile):
                audit = self.declaration(profile=profile)
                self.assertNotIn('outcome_label', audit.sources[CAPTURE]['use_roles'])
                self.assertTrue(any(c['status'] == 'FAIL' for c in audit.checks))

    def test_runtime_profile_executes_actual_source_reproduction(self):
        audit = self.declaration()
        self.assertEqual(audit.sources[CAPTURE]['use_roles'], ['outcome_label'])
        self.assertGreaterEqual(audit.points, 22990)
        self.assertIn(CAPSULE, audit.consumed)
        self.assertGreater(audit.read_bytes, 14_000_000)
        self.assertGreaterEqual(audit.sources[CAPTURE]['available_at'], self.review['reviewed_at'])

    def test_runtime_duplicate_review_json_cannot_grant_role(self):
        audit = self.declaration(duplicate_json=True)
        self.assertNotIn('outcome_label', audit.sources[CAPTURE]['use_roles'])

    def test_actual_parent_audit_five_positive_units_and_no_complete_ledger_or_negative(self):
        import evidence_audit as ea
        self.declaration()
        result=ea.audit_evidence(self.root,'2026-09-28',verified_at=NOW)
        self.assertNotIn(result['status'],['FAIL','BLOCKED'])
        events=result['capture_audit']['events']
        self.assertEqual(sum(e['canonical_eligible'] for e in events),5)
        self.assertEqual(sum(e['capture_count'] for e in events),6)
        self.assertEqual(sum(u.get('label')==1 for u in result['observation_units']),5)
        self.assertEqual(sum(u.get('label')==0 for u in result['observation_units']),0)
        self.assertEqual(result['outcome_ledger']['denominator_coverage'],'NOT_ESTABLISHED')

    def test_parent_final_rescan_charges_shared_remaining_budget(self):
        import evidence_audit as ea
        self.declaration()
        audit=ea.Audit(self.root,NOW)
        previous=[]
        def exhaust(a):
            previous.append(a.read_bytes)
            ea.MAX_READ_BYTES=a.read_bytes+1
            return {}
        with patch.object(ea,'MAX_READ_BYTES',ea.MAX_READ_BYTES),patch.object(ea,'Audit',return_value=audit),patch.object(ea,'_recovered',exhaust):
            result=ea.audit_evidence(self.root,'2026-09-28',verified_at=NOW)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['observation_units'],[])
        self.assertEqual(audit.read_bytes,previous[0]+2)

    def test_expiry_during_successful_result_hash_never_returns_units(self):
        import evidence_audit as ea
        self.declaration()
        audit=ea.Audit(self.root,NOW);real_digest=ea.digest
        def expire(value):
            sha=real_digest(value)
            if isinstance(value,dict) and 'observation_units' in value and value.get('status') not in ('BLOCKED','FAIL'):
                audit.deadline=-1
            return sha
        with patch.object(ea,'Audit',return_value=audit),patch.object(ea,'digest',expire):
            result=ea.audit_evidence(self.root,'2026-09-28',verified_at=NOW)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['observation_units'],[])

    @unittest.skipUnless(os.name=='nt','Windows native junction regression')
    def test_native_junctions_guard_csv_review_capsule_and_root_before_external_read(self):
        import evidence_audit as ea
        self.declaration(profile=None)
        for relative in ['data/processed/capture_events/2026','evidence/source_reviews',
                         'evidence/source_reviews/capsules']:
            with self.subTest(relative=relative),tempfile.TemporaryDirectory() as outside_tmp:
                link=self.root/relative; external=Path(outside_tmp)/'payload'
                self.assertTrue(link.absolute().is_relative_to(self.root.absolute()))
                self.assertTrue(external.absolute().is_relative_to(Path(outside_tmp).absolute()))
                link.rename(external)
                created=False
                try:
                    made=subprocess.run(['cmd','/c','mklink','/J',str(link),str(external)],capture_output=True)
                    self.assertEqual(made.returncode,0,made.stderr.decode(errors='replace'))
                    created=True;self.assertTrue(link.is_junction())
                    opened=[];original=Path.open
                    def guarded(path,*args,**kwargs):
                        if path.resolve().is_relative_to(external.resolve()):
                            opened.append(path);raise AssertionError('external payload opened')
                        return original(path,*args,**kwargs)
                    # A known valid profile is required for the capsule path to
                    # be reached, while missing-profile review reads stay guarded.
                    if relative.endswith('/capsules'):
                        review=deepcopy(self.review);review['use_roles']=['outcome_label']
                        write(self.root,REVIEW_PATH,canonical_bytes(review))
                        ref=dict(path=REVIEW_PATH,sha256=hashlib.sha256(canonical_bytes(review)).hexdigest(),size_bytes=len(canonical_bytes(review)))
                        write(self.root,'policies/observation_evidence.json',canonical_bytes(dict(schema_version='1.0',sources=[dict(self.review['source_refs']['captures'],review_ref=ref)])))
                    with patch.object(Path,'open',guarded):
                        audit=ea.Audit(self.root,NOW);ea._declarations(audit)
                    self.assertEqual(opened,[])
                    self.assertNotIn('outcome_label',audit.sources.get(CAPTURE,{}).get('use_roles',[]))
                    self.assertTrue(any(c['status']=='FAIL' for c in audit.checks))
                finally:
                    if created:os.rmdir(link)  # remove only the junction itself
                    external.rename(link)
        with tempfile.TemporaryDirectory() as aliases:
            alias=Path(aliases)/'linked-root'
            made=subprocess.run(['cmd','/c','mklink','/J',str(alias),str(self.root)],capture_output=True)
            self.assertEqual(made.returncode,0)
            try:
                with patch.object(Path,'open',side_effect=AssertionError('root junction payload opened')):
                    audit=ea.Audit(alias,NOW);ea._declarations(audit)
                self.assertTrue(any(c['status']=='FAIL' for c in audit.checks))
            finally:os.rmdir(alias)


class AuditReadBoundaryTests(unittest.TestCase):
    def setUp(self):
        from evidence_audit import Audit
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'evidence/input'
        write(self.root, 'evidence/input', b'abc')
        self.audit = Audit(self.root, NOW)

    def test_growth_after_stat_is_bounded_and_actual_bytes_charge_shared_budget(self):
        from evidence_audit import AuditBudgetExceeded
        stat = Path.stat
        grown = False
        def grow(path, *args, **kwargs):
            nonlocal grown
            result = stat(path, *args, **kwargs)
            if path == self.path and kwargs.get('follow_symlinks', True) and not grown:
                grown = True
                with self.path.open('ab') as handle:
                    handle.write(b'123456789')
            return result
        with patch('evidence_audit.MAX_READ_BYTES', 5), patch.object(Path, 'stat', grow):
            with self.assertRaises(AuditBudgetExceeded):
                self.audit.read('evidence/input')
        self.assertEqual(self.audit.read_bytes, 6)

    def test_ref_expected_size_rejects_bool_negative_huge_and_mismatch(self):
        sha = hashlib.sha256(b'abc').hexdigest()
        for size in [True, -1, 0, 2, 4, 1 << 40, None]:
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.audit.ref(dict(path='evidence/input', sha256=sha, size_bytes=size))
        self.assertEqual(self.audit.ref(dict(path='evidence/input', sha256=sha)), b'abc')
        self.assertEqual(self.audit.ref(dict(path='evidence/input', sha256=sha, size_bytes=3)), b'abc')


if __name__ == '__main__':
    unittest.main()
