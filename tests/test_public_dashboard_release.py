"""Synthetic data only: authenticated private source to allowlisted public totals."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.apply_private_dashboard_overlay import apply_overlay
from tools.dashboard_release import habu_library_vault_tool as vault
try:
    from tools.dashboard_release import public_summary as public
    from tools.dashboard_release import vault_dashboard as bridge
except ImportError:
    public = bridge = None

CANARY = 'PRIVATE-EXACT-COORDINATE-AND-KEY-CANARY-DO-NOT-EXPORT'


def example_inputs():
    base = {'schema_version':'habu-capture-dashboard-v2', 'year':2026,
        'asof':'2026-10-30', 'total':2,
        'months':[{'key':'2026-10','n':2,'cum':2}],
        'nights':[{'night':'2026-10-27','month':'2026-10','count':2,
            'effort_confirmed':True,'effort_status':'CAPTURE_CONFIRMED_NIGHT',
            'note':CANARY}], 'undated_captures':[], 'undated_count':0,
        'warnings':[CANARY], 'effort':{}, 'effort_months':[]}
    overlay = {'schema_version':'habu-private-dashboard-owner-overlay-v1',
        'source':'OWNER_LOG_AND_GPX_PRIVATE_REVIEW', 'private_only':True,
        'nights':[
            {'night':'2026-12-01','capture_count':2,'session_kind':'SEARCH','gpx_time_place_crosscheck':True},
            {'night':'2026-12-05','capture_count':0,'session_kind':'SEARCH','gpx_time_place_crosscheck':True},
            {'night':'2026-12-07','capture_count':0,'session_kind':'RESEARCH_NON_SEARCH','gpx_time_place_crosscheck':False}],
        'expected_monthly':{'2026-12':2}, 'owner_claimed_total':3,
        'research_models':{'official_100m_10min_status':'BLOCKED',
            'night_count':{'training_nights':3,'owner_captures':4,'mode':'REFERENCE_ONLY'},
            'recorded_capture_clock':{'event_records':4,'mode':'REFERENCE_ONLY'},
            'positive_spatial':{'positive_events':3,'individual_units':4,'mode':'REFERENCE_ONLY'},
            'status_note':CANARY}}
    return base, overlay


class PublicProjectionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(public, 'aggregate-only projection is not implemented')
        b,o = example_inputs()
        self.private = apply_overlay(b,o)

    def test_preserves_totals_discrepancy_and_excludes_survey_effort(self):
        out = public.project_public_summary(self.private)
        self.assertEqual(out['capture_total'],4)
        self.assertEqual(out['owner_reported_total'],3)
        self.assertEqual(out['total_difference'],1)
        self.assertEqual(out['capture_total_status'],'UNRECONCILED')
        self.assertEqual(out['effort_nights'],3)
        self.assertEqual(out['non_search_days'],1)
        self.assertEqual(out['months'][1]['zero_nights'],1)
        self.assertEqual(out['official_model_status'],'BLOCKED')

    def test_projection_has_no_private_notes_times_paths_or_source_keys(self):
        self.private['private_context']={'secret':CANARY,'latitude':28.12345678}
        text=json.dumps(public.project_public_summary(self.private),ensure_ascii=False)
        for forbidden in (CANARY,'private_context','2026-12-01','latitude','28.12345678','key_b64'):
            self.assertNotIn(forbidden,text)

    def test_no_model_authority_upgrade(self):
        self.private['research_models']['official_100m_10min_status']='PASS'
        with self.assertRaises(ValueError):public.project_public_summary(self.private)

    def test_inconsistent_capture_total_rejected(self):
        self.private['total']+=1
        with self.assertRaises(ValueError):public.project_public_summary(self.private)

    def test_inconsistent_month_sum_rejected(self):
        self.private['months'][0]['n']+=1
        with self.assertRaises(ValueError):public.project_public_summary(self.private)

    def test_duplicate_nights_rejected(self):
        self.private['nights'].append(copy.deepcopy(self.private['nights'][0]))
        with self.assertRaises(ValueError):public.project_public_summary(self.private)

    def test_nonsearch_positive_rejected(self):
        self.private['nights'][-1]['count']=1
        with self.assertRaises(ValueError):public.project_public_summary(self.private)

    def test_bool_count_and_invalid_dates_rejected(self):
        for change in ('bool','date'):
            d=copy.deepcopy(self.private)
            if change=='bool':d['nights'][0]['count']=True
            else:d['nights'][0]['night']='2026-13-55'
            with self.subTest(change=change),self.assertRaises(ValueError):public.project_public_summary(d)

    def test_unknown_public_field_rejected(self):
        d=public.project_public_summary(self.private);d['extra']=CANARY
        with self.assertRaises(ValueError):public.validate_public_summary(d)

    def test_unknown_nested_public_field_rejected(self):
        d=public.project_public_summary(self.private);d['months'][0]['note']=CANARY
        with self.assertRaises(ValueError):public.validate_public_summary(d)

    def test_invalid_public_numeric_and_model_types_rejected(self):
        for field,value in [('capture_total',True),('effort_nights',float('nan'))]:
            d=public.project_public_summary(self.private);d[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):public.validate_public_summary(d)
        d=public.project_public_summary(self.private);d['models'][0]['kind']=CANARY
        with self.assertRaises(ValueError):public.validate_public_summary(d)

    def test_private_strings_cannot_be_accepted_as_model_counts(self):
        self.private['research_models']['night_count']['training_nights']=CANARY
        with self.assertRaises(ValueError):public.project_public_summary(self.private)

    def test_full_history_model_is_distinct_from_elapsed_time_subset(self):
        self.private['research_models']['all_owner_search_night_research']={
            'search_nights':3,'captures':4,'status':'RESEARCH_ONLY_UNRECONCILED_269_VS_270'}
        out=public.project_public_summary(self.private)
        row=next((x for x in out['models'] if x['kind']=='all_owner_nights'),None)
        self.assertIsNotNone(row)
        self.assertEqual((row['nights'],row['individuals']),(3,4))
        self.assertEqual(row['status'],'RESEARCH_ONLY')

    def test_output_is_deterministic_despite_private_build_timestamp(self):
        first=public.project_public_summary(self.private)
        self.private['generated_at_utc']='2030-01-01T00:00:00Z'
        self.assertEqual(public.project_public_summary(self.private),first)


class EncryptedReleaseTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(bridge, 'encrypted dashboard bridge is not implemented')
        self.tmp=tempfile.TemporaryDirectory(prefix='synthetic-habu-release-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.private=self.root/'private';self.private.mkdir()
        originals=self.private/'originals';originals.mkdir()
        b,o=example_inputs()
        for name,value in [('2026-11-25-base.txt',b),('2026-11-25-overlay.txt',o)]:
            (originals/name).write_text(json.dumps(value,ensure_ascii=False))
        for i in range(17):(originals/f'2026-12-02-filler-{i}.txt').write_text(CANARY+str(i))
        self.vault=self.private/'originals.enc.zip';self.key=self.private/'owner.key.json'
        vault.create(originals,self.vault,self.key,self.private/'receipt.json')
        self.dest=self.root/'public-release'
        self.template=ROOT/'dashboard/public-summary.html'
        self.kwargs={
          'archive':self.vault,'key_file':self.key,
          'base_entry':'2026/11/2026-11-25-base.txt',
          'overlay_entry':'2026/11/2026-11-25-overlay.txt',
          'destination':self.dest,'template':self.template,
          'expected_archive_sha256':hashlib.sha256(self.vault.read_bytes()).hexdigest(),
          'expected_base_sha256':hashlib.sha256((originals/'2026-11-25-base.txt').read_bytes()).hexdigest(),
          'expected_overlay_sha256':hashlib.sha256((originals/'2026-11-25-overlay.txt').read_bytes()).hexdigest()}
        self.synthetic_env=patch.dict(os.environ,{'GITHUB_ACTIONS':'false'})
        self.synthetic_env.start();self.addCleanup(self.synthetic_env.stop)

    def run_release(self, **changes):
        return bridge.build_from_vault(**dict(self.kwargs,**changes))

    def test_real_crypto_roundtrip_projects_only_aggregates(self):
        before=self.key.read_bytes();result=self.run_release()
        self.assertEqual(result['status'],'AGGREGATE_RELEASE_VERIFIED')
        self.assertEqual(result['authenticated_source_files'],19)
        self.assertEqual(self.key.read_bytes(),before)
        files={p.relative_to(self.dest).as_posix() for p in self.dest.rglob('*') if p.is_file()}
        self.assertEqual(files,{'index.html','data/public_summary.json','_headers'})
        combined=b'\n'.join(p.read_bytes() for p in self.dest.rglob('*') if p.is_file())
        for secret in (CANARY.encode(),json.loads(before)['key_b64'].encode(),b'2026-12-01',b'<trkpt'):
            self.assertNotIn(secret,combined)
        self.assertEqual(json.loads((self.dest/'data/public_summary.json').read_text())['capture_total'],4)

    def test_same_source_rerun_is_idempotent(self):
        a=self.run_release();b=self.run_release()
        self.assertEqual(a['public_summary_sha256'],b['public_summary_sha256'])
        self.assertTrue(b['identical_existing_release'])

    def test_existing_foreign_file_prevents_overwrite(self):
        self.dest.mkdir();(self.dest/'key.json').write_text(CANARY)
        with self.assertRaises(ValueError):self.run_release()
        self.assertEqual((self.dest/'key.json').read_text(),CANARY)

    def test_wrong_key_produces_no_release(self):
        p=self.private/'wrong-key.json';o=json.loads(self.key.read_bytes())
        import base64
        o['key_b64']=base64.b64encode(bytes(32)).decode();p.write_text(json.dumps(o))
        with self.assertRaises(ValueError):self.run_release(key_file=p)
        self.assertFalse(self.dest.exists())

    def test_archive_hash_mismatch_produces_no_release(self):
        with self.assertRaises(ValueError):self.run_release(expected_archive_sha256='0'*64)
        self.assertFalse(self.dest.exists())

    def test_ciphertext_tamper_rejected_even_with_matching_outer_hash(self):
        bad=self.private/'tampered.enc.zip'
        with zipfile.ZipFile(self.vault) as z,zipfile.ZipFile(bad,'w') as out:
            changed=False
            for info in z.infolist():
                content=z.read(info.filename)
                if info.filename.endswith('.enc') and not changed:
                    content=content[:-1]+bytes([content[-1]^1]);changed=True
                out.writestr(info.filename,content)
        with self.assertRaises(ValueError):self.run_release(archive=bad,expected_archive_sha256=hashlib.sha256(bad.read_bytes()).hexdigest())
        self.assertFalse(self.dest.exists())

    def test_plain_source_hash_mismatch_produces_no_release(self):
        with self.assertRaises(ValueError):self.run_release(expected_base_sha256='0'*64)
        self.assertFalse(self.dest.exists())

    def test_unknown_private_entry_produces_no_release(self):
        with self.assertRaises(ValueError):self.run_release(base_entry='2026/12/missing.txt')
        self.assertFalse(self.dest.exists())

    def test_symlink_key_rejected(self):
        p=self.root/'symlink-key';p.symlink_to(self.key)
        with self.assertRaises(ValueError):self.run_release(key_file=p)
        self.assertFalse(self.dest.exists())

    def test_public_actions_runtime_is_blocked(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),self.assertRaises(ValueError):self.run_release()
        self.assertFalse(self.dest.exists())

    def test_cannot_write_release_inside_private_input_directory(self):
        with self.assertRaises(ValueError):self.run_release(destination=self.private/'web')
        self.assertFalse((self.private/'web').exists())

    def test_missing_template_token_fails_without_output(self):
        p=self.root/'broken.html';p.write_text('<html>missing marker</html>')
        with self.assertRaises(ValueError):self.run_release(template=p)
        self.assertFalse(self.dest.exists())

    def test_private_inputs_inside_git_rejected(self):
        (self.private/'.git').mkdir()
        with self.assertRaises(ValueError):self.run_release()
        self.assertFalse(self.dest.exists())

if __name__=='__main__':unittest.main()
