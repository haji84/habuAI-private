import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_capture_dashboard import DataAuditError, operating_night, build

ROOT = Path(__file__).resolve().parents[1]

class CaptureDashboardTests(unittest.TestCase):
    def sandbox(self):
        tmp = tempfile.TemporaryDirectory()
        repo = Path(tmp.name)
        (repo / 'dashboard').mkdir()
        (repo / 'dashboard/baseline_2026.json').write_bytes((ROOT / 'dashboard/baseline_2026.json').read_bytes())
        return tmp, repo

    def add_raw(self, repo, date, events, filename='night.json'):
        folder = repo / 'data/raw/habu_logs/2026'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / filename).write_text(json.dumps({'schema_version':'habu-night-log-v2','operational_date':date,'source':'user Habu log','events':events},ensure_ascii=False), encoding='utf-8')

    def test_base_has_238_not_double_counted(self):
        result = build(ROOT)
        self.assertEqual(result['total'], 238)
        self.assertEqual([m['n'] for m in result['months']], [8,23,60,35,45,50,17])
        self.assertEqual(result['new_confirmed_nights'], 0)

    def test_boundary(self):
        self.assertEqual(operating_night('2026-10-22T06:59:59+09:00'), '2026-10-21')
        self.assertEqual(operating_night('2026-10-22T07:00:00+09:00'), '2026-10-22')
        with self.assertRaises(DataAuditError): operating_night('2026-10-22T06:59:00')

    def test_new_raw_is_added_once_and_sightings_ignored(self):
        tmp, repo = self.sandbox()
        try:
            self.add_raw(repo,'2026-10-21',[
                {'event_id':'a','time_local':'2026-10-21T23:00:00+09:00','place':'X','type':'capture','individual_count':2},
                {'event_id':'b','time_local':'2026-10-22T01:00:00+09:00','place':'Y','type':'sighting','individual_count':10},
                {'event_id':'c','time_local':'2026-10-22T00:15:00+09:00','place':'X','type':'capture','capture_owner':'other','individual_count':1},
            ])
            result = build(repo)
            self.assertEqual(result['total'],240)
            self.assertEqual(result['months'][-1]['n'],19)
            self.assertEqual(result['new_confirmed_nights'],1)
            self.assertNotIn('latitude',json.dumps(result))
        finally: tmp.cleanup()

    def test_raw_processed_overlap_not_double_counted(self):
        tmp,repo=self.sandbox()
        try:
            self.add_raw(repo,'2026-10-21',[{'event_id':'a','time_local':'2026-10-21T23:00:00+09:00','place':'X','type':'capture','individual_count':2}])
            folder=repo/'data/processed/individuals/2026';folder.mkdir(parents=True)
            (folder/'2026-10-21.csv').write_text('individual_id,operational_date,event_time_local,capture_owner\na,2026-10-21,2026-10-21T23:00:00+09:00,self\nb,2026-10-21,2026-10-21T23:00:00+09:00,self\n')
            self.assertEqual(build(repo)['total'],240)
            (folder/'2026-10-21.csv').write_text('individual_id,operational_date,event_time_local,capture_owner\na,2026-10-21,2026-10-21T23:00:00+09:00,self\n')
            with self.assertRaises(DataAuditError): build(repo)
        finally:tmp.cleanup()

    def test_duplicate_event_blocks_instead_of_double_count(self):
        tmp,repo=self.sandbox()
        try:
            event={'event_id':'a','time_local':'2026-10-21T23:00:00+09:00','place':'X','type':'capture','individual_count':1}
            self.add_raw(repo,'2026-10-21',[event],filename='one.json')
            self.add_raw(repo,'2026-10-21',[event,{'event_id':'b','time_local':'2026-10-21T23:01:00+09:00','place':'X','type':'capture','individual_count':1}],filename='two.json')
            with self.assertRaises(DataAuditError):build(repo)
        finally:tmp.cleanup()

    def test_old_night_is_unchanged(self):
        tmp,repo=self.sandbox()
        try:
            self.add_raw(repo,'2026-09-28',[{'event_id':'a','time_local':'2026-09-28T22:00:00+09:00','place':'X','type':'capture','individual_count':6}])
            self.assertEqual(build(repo)['total'],238)
        finally:tmp.cleanup()

if __name__=='__main__':unittest.main()
