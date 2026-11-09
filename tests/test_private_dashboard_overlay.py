"""Synthetic-only regression tests: source classification, privacy and number integrity."""
import copy
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
try:
    from scripts.apply_private_dashboard_overlay import apply_overlay
except ImportError:
    from apply_private_dashboard_overlay import apply_overlay

class OwnerPrivateDashboardOverlayTests(unittest.TestCase):
    def setUp(self):
        self.base={
            'schema_version':'habu-capture-dashboard-v2','asof':'2026-10-30',
            'months':[{'key':'2026-10','n':2,'cum':2}],'total':2,
            'nights':[{'night':'2026-10-27','month':'2026-10','count':2,
                       'effort_confirmed':True,'effort_status':'CAPTURE_CONFIRMED_NIGHT'}],
            'effort':{},'effort_months':[], 'new_confirmed_nights':1,'warnings':[]
        }
        self.overlay={
            'schema_version':'habu-private-dashboard-owner-overlay-v1',
            'source':'OWNER_LOG_AND_GPX_PRIVATE_REVIEW','private_only':True,
            'nights':[
                {'night':'2026-12-01','capture_count':2,'session_kind':'SEARCH','gpx_time_place_crosscheck':True},
                {'night':'2026-12-05','capture_count':0,'session_kind':'SEARCH','gpx_time_place_crosscheck':True},
                {'night':'2026-12-07','capture_count':0,'session_kind':'RESEARCH_NON_SEARCH','gpx_time_place_crosscheck':False},
            ],
            'expected_monthly':{'2026-12':2},'owner_claimed_total':3,
            'research_models':{'official_100m_10min_status':'BLOCKED'}
        }
    def test_adds_once_and_tallies(self):
        out=apply_overlay(self.base,self.overlay)
        self.assertEqual(out['total'],4)
        self.assertEqual(out['months'][-1]['n'],2)
        self.assertEqual(out['effort']['total_nights'],3)
        self.assertEqual(out['effort']['positive_nights'],2)
        self.assertEqual(out['effort']['zero_nights'],1)
        self.assertEqual(out['private_tally_reconciliation']['difference_log_minus_reported'],1)
        self.assertEqual(self.base['total'],2)
    def test_survey_night_is_not_zero_search(self):
        out=apply_overlay(self.base,self.overlay)
        nonsearch=next(x for x in out['nights'] if x['night']=='2026-12-07')
        self.assertFalse(nonsearch['effort_confirmed'])
        self.assertEqual(nonsearch['effort_status'],'EXCLUDED_NOT_SEARCH')
    def test_nonsearch_cannot_capture(self):
        o=copy.deepcopy(self.overlay);o['nights'][-1]['capture_count']=1
        with self.assertRaises(ValueError):apply_overlay(self.base,o)
    def test_overlay_must_not_include_coordinates(self):
        o=copy.deepcopy(self.overlay);o['nights'][0]['latitude']=28.1
        with self.assertRaises(ValueError):apply_overlay(self.base,o)
    def test_reject_duplicate_nights(self):
        o=copy.deepcopy(self.overlay);o['nights'].append(o['nights'][0])
        with self.assertRaises(ValueError):apply_overlay(self.base,o)
    def test_refuse_rewriting_historic_baseline(self):
        o=copy.deepcopy(self.overlay);o['nights'].append({'night':'2026-10-27','capture_count':3,'session_kind':'SEARCH','gpx_time_place_crosscheck':True})
        with self.assertRaises(ValueError):apply_overlay(self.base,o)
    def test_reject_inconsistent_month_total(self):
        o=copy.deepcopy(self.overlay);o['expected_monthly']['2026-12']=3
        with self.assertRaises(ValueError):apply_overlay(self.base,o)
    def test_no_automatic_formal_promotion(self):
        o=copy.deepcopy(self.overlay);o['research_models']['official_100m_10min_status']='PASS'
        with self.assertRaises(ValueError):apply_overlay(self.base,o)
    def test_reject_untrusted_source(self):
        o=copy.deepcopy(self.overlay);o['source']='any unaudited file'
        with self.assertRaises(ValueError):apply_overlay(self.base,o)

if __name__=='__main__':unittest.main()