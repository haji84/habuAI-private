"""Regression: one 2026-09-29 00:00 capture EVENT holds two INDIVIDUAL Habu.

This is intentionally separate from old historical transport tests, which must
retain the 50 original September event rows as immutable audit history.
"""
import csv
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def rows(relative):
    with (ROOT/relative).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

class SeptemberMultiplicityTests(unittest.TestCase):
    def test_one_encounter_two_individuals(self):
        captures=rows("data/processed/capture_events/2026/2026-09-28.csv")
        individuals=rows("data/processed/individuals/2026/2026-09-28.csv")
        self.assertEqual(len(captures),5)
        self.assertEqual(sum(int(x["event_count"]) for x in captures),6)
        self.assertEqual(len(individuals),6)
        at_midnight=[x for x in captures
                     if x["event_time_local"]=="2026-09-29T00:00:00+09:00"]
        self.assertEqual(len(at_midnight),1)
        event=at_midnight[0]
        self.assertEqual(int(event["event_count"]),2)
        self.assertEqual(event["operational_date"],"2026-09-28")
        linked=[x for x in individuals if x["event_id"]==event["event_id"]]
        self.assertEqual(len(linked),2)
        self.assertEqual({x["individual_index"] for x in linked},{"1","2"})
        self.assertEqual({x["event_time_local"] for x in linked},
                         {"2026-09-29T00:00:00+09:00"})

    def test_other_sources_not_counted_as_owner_capture(self):
        captures=rows("data/processed/capture_events/2026/2026-09-28.csv")
        self.assertTrue(all(x["event_type"]=="capture" for x in captures))

if __name__=="__main__":
    unittest.main()
