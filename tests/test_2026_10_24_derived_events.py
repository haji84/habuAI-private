"""2026-10-24 Chat-derived 39-event review CSV is NOT native source or model labels."""
from __future__ import annotations
import csv
import hashlib
import unittest
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CSV_FILE=ROOT/"incoming/habu_logs/2026-10-24/2026-10-24_owner-chat_39events_derived.csv"
EXPECTED_SHA="d5b07cec456bd4aeaf1bfce3037919eba88949181126462e7d61595d9e8eb95f"

class October24OwnerChatEventTests(unittest.TestCase):
    def test_derived_source_byte_identity_and_separate_species_roles(self):
        data=CSV_FILE.read_bytes()
        self.assertEqual(len(data),7838)
        self.assertEqual(hashlib.sha256(data).hexdigest(),EXPECTED_SHA)
        with CSV_FILE.open(encoding="utf-8-sig",newline="") as handle:
            rows=list(csv.DictReader(handle))
        self.assertEqual(len(rows),39)
        self.assertEqual(Counter(x["kind"] for x in rows),{"目撃":32,"捕獲":4,"轢死":3})
        self.assertEqual(sum(int(x["quantity"]) for x in rows if x["kind"]=="目撃"),34)
        self.assertEqual(sum(int(x["quantity"]) for x in rows if x["kind"]=="捕獲"),4)
        self.assertEqual(sum(x["kind"]=="轢死" and x["species_or_description"]=="ハブ" for x in rows),1)
        self.assertTrue(all(x["source_kind"]=="user_chat_original_text_transcribed" for x in rows))
        self.assertTrue(all(x["training_label"]=="" for x in rows))
        self.assertEqual(len({x["event_id"] for x in rows}),39)

    def test_unobserved_gap_capture_remains_unobserved(self):
        with CSV_FILE.open(encoding="utf-8-sig",newline="") as handle:
            rows=list(csv.DictReader(handle))
        first=next(x for x in rows if x["local_time"]=="2026-10-24T20:27:00+09:00")
        self.assertEqual(first["kind"],"捕獲")
        self.assertEqual(first["gpx_observation_quality"],"TIME_GAP_UNOBSERVED")
        self.assertEqual(first["training_label"],"")
        self.assertEqual(Counter(x["gpx_observation_quality"] for x in rows),
                         {"TIME_GAP_UNOBSERVED":14,"SUPPORTED_EVENT_TIME_SPACE":25})
        # Captures after midnight belong to Oct24 exploration night (JST 07:00).
        for x in rows:
            if x["kind"]=="捕獲":
                dt=datetime.fromisoformat(x["local_time"])
                self.assertEqual((dt-timedelta(days=1) if dt.hour<7 else dt).date().isoformat(),"2026-10-24")

if __name__=="__main__":
    unittest.main()
