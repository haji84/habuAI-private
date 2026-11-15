"""Synthetic-only safety and regression checks for candidate-feature diagnostics."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.habu_pdca_research.feature_candidates import (
    duration_candidate,region_candidate_area_match,field_station_temperature_candidate
)

R={'night':'2026-11-11','source_category':'REFERENCE_BEFORE_SEARCH','planned_hours':4.5,
   'actual_captures':1,'issued_at':'2026-11-11T17:45:00+09:00',
   'first_capture_at':'2026-11-11T19:20:00+09:00'}

class CandidateTests(unittest.TestCase):
    def test_train_test_separation(self):
        with self.assertRaisesRegex(ValueError,'TRAIN_TEST_TIME_LEAK'):
            duration_candidate(.47,'2026-11-11',[R])
    def test_preissued_planned_effort_not_actual_duration(self):
        row=duration_candidate(.5,'2026-11-09',[R])
        self.assertEqual(row['rows'][0]['baseline_lambda'],2.5)
        self.assertEqual(row['rows'][0]['plan_conditional_lambda'],2.25)
        self.assertTrue(row['retrospective_actual_elapsed_never_used_as_predictor'])
        self.assertFalse(row['official_model_eligible'])
    def test_no_post_capture_predictions(self):
        wrong={**R,'issued_at':'2026-11-11T19:30:00+09:00'}
        with self.assertRaisesRegex(ValueError,'FORECAST_AFTER_FIRST_CAPTURE'):
            duration_candidate(.5,'2026-11-09',[wrong])
    def test_invalid_phase_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):duration_candidate(.5,'2026-11-09',[{**R,'source_category':'AFTER_OUTCOME'}])
        with self.assertRaises(ValueError):duration_candidate(float('nan'),'2026-11-09',[R])
    def test_region_never_converts_unvisited_to_zero(self):
        row={'night':'2026-11-13','actual_captures':2,
             'area_diagnostic':{'known_settlement_capture_count':1,'unknown_or_generic_area_capture_count':1,
                                'primary_A_name_matches':1,'alternate_name_matches':{'B':0,'C':0}}}
        out=region_candidate_area_match([row]);self.assertIsNone(out['area_top10_recall'])
        self.assertIsNone(out['region_ranked_exposure_denominators'])
        self.assertTrue(out['unsearched_areas_are_not_negative'])
    def test_region_denominator_and_overcount(self):
        base={'night':'2026-11-13','actual_captures':1,'area_diagnostic':{
             'known_settlement_capture_count':1,'unknown_or_generic_area_capture_count':1,
             'primary_A_name_matches':0,'alternate_name_matches':{'B':0,'C':0}}}
        with self.assertRaisesRegex(ValueError,'AREA_DENOMINATOR_CONFLICT'):region_candidate_area_match([base])
        base['area_diagnostic']['unknown_or_generic_area_capture_count']=0
        base['area_diagnostic']['primary_A_name_matches']=2
        with self.assertRaisesRegex(ValueError,'AREA_OVERCOUNT'):region_candidate_area_match([base])
    def station(self):
        return [{'station_id':'88901','support_kind':'HOURLY_REFERENCE_STATION',
                 'valid_end':f'2026-11-{day:02d}T20:00:00+09:00',
                 'values':{'temperature_c':{'kind':'OBSERVED','quality':'NORMAL','value':21}}}
                for day in (9,11,13)]
    def field(self):
        return [{'night':f'2026-11-{day:02d}','observed_at':f'2026-11-{day:02d}T20:15:00+09:00','temperature_c':val}
                for day,val in [(9,19),(11,20),(13,17)]]
    def test_weather_night_forward_no_same_night_training(self):
        out=field_station_temperature_candidate(self.station(),self.field())
        self.assertEqual(out['field_station_pairs'],3)
        self.assertEqual(out['future_night_calibration_evaluation_nights'],2)
        self.assertEqual(out['trained_offset_history'][0]['offset_from_prior_nights_c'],None)
        self.assertEqual(out['trained_offset_history'][1]['offset_from_prior_nights_c'],-2)
        self.assertEqual(out['trained_offset_history'][2]['offset_from_prior_nights_c'],-1.5)
    def test_future_station_observation_not_joined(self):
        station=self.station()
        out=field_station_temperature_candidate(station,[{'night':'2026-11-09','observed_at':'2026-11-09T19:59:00+09:00','temperature_c':20}])
        self.assertEqual(out['point_records'][0]['pair_status'],'MISSING_PRECEDING_STATION_HOUR')
    def test_station_identity(self):
        wrong=self.station();wrong[0]['station_id']='12345'
        with self.assertRaisesRegex(ValueError,'UNTRUSTED_REFERENCE_STATION'):
            field_station_temperature_candidate(wrong,self.field())
    def test_duplicate_field_temperature(self):
        f=self.field()
        with self.assertRaisesRegex(ValueError,'DUPLICATE_FIELD_TEMPERATURE_RECORD'):
            field_station_temperature_candidate(self.station(),f+[f[0]])
    def test_timezone_offset(self):
        wrong=self.field();wrong[0]['observed_at']='2026-11-09T20:15:00'
        with self.assertRaisesRegex(ValueError,'OFFSET_AWARE_REQUIRED'):
            field_station_temperature_candidate(self.station(),wrong)

if __name__=='__main__':unittest.main()
