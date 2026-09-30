import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SPEC=importlib.util.spec_from_file_location("pdca", Path(__file__).parents[1]/"scripts"/"run_pdca.py")
pdca=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(pdca)

def test_operational_night_before_0700_is_previous_day():
    assert pdca.operational_night(datetime(2026,9,30,6,59,tzinfo=ZoneInfo("Asia/Tokyo")))=="2026-09-29"

def test_operational_night_at_0700_is_current_day():
    assert pdca.operational_night(datetime(2026,9,30,7,0,tzinfo=ZoneInfo("Asia/Tokyo")))=="2026-09-30"

def test_missing_predictions_blocks_pipeline(tmp_path):
    result=pdca.run(tmp_path,"2026-09-30")
    assert result["overall_status"]=="BLOCKED"
    assert result["stages"][0]["name"]=="load_frozen_predictions"
    assert result["stages"][0]["status"]=="BLOCKED"

def test_prediction_versions_are_discovered_in_numeric_order(tmp_path):
    base=tmp_path/"predictions"/"original"/"2026-09-30"
    for name in ("P10","P2","P0","P1"):
        (base/name).mkdir(parents=True)
    assert [p.name for p in pdca.discover_predictions(tmp_path,"2026-09-30")]==["P0","P1","P2","P10"]
