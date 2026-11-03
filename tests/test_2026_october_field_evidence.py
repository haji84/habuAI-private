"""Independent raw-evidence regression tests for four October exploration nights.

The tests deliberately do not manufacture/score historical ORIGINAL forecasts.
"""
import csv
import hashlib
import json
import math
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NIGHTS = ("2026-10-06", "2026-10-08", "2026-10-14", "2026-10-15")


def operational_night(instant):
    local = instant
    if local.hour < 7:
        local -= timedelta(days=1)
    return local.date().isoformat()


def raw_gpx(night):
    manifest = json.loads((ROOT / "evidence/gpx/2026" / (night + ".manifest.json")).read_text(encoding="utf-8"))
    storage = manifest["storage"]
    if storage["type"] == "direct-gpx":
        payload = (ROOT / storage["path"]).read_bytes()
    elif storage["type"] == "line-gpx-archive-v1":
        directory = ROOT / storage["path"]
        archive = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        parts = sorted(directory.glob(archive["part_glob"]))
        if len(parts) != archive["part_count"]:
            raise ValueError("GPX archive part count mismatch: " + night)
        payload = "\n".join(p.read_text(encoding="utf-8") for p in parts).encode("utf-8")
        if hashlib.sha256(payload).hexdigest() != archive["raw_sha256"]:
            raise ValueError("GPX archive SHA mismatch: " + night)
    else:
        raise ValueError("Unrecognized raw GPX storage type")
    if len(payload) != manifest["raw_size_bytes"]:
        raise ValueError("Raw byte size mismatch: " + night)
    if hashlib.sha256(payload).hexdigest() != manifest["raw_sha256"]:
        raise ValueError("Raw SHA mismatch: " + night)
    return payload, manifest


def points(raw):
    root = ET.fromstring(raw)
    result = []
    for item in root.iter():
        if not item.tag.endswith("trkpt"):
            continue
        t = next((e.text for e in item if e.tag.endswith("time")), None)
        if t is None:
            continue
        dt = datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone()
        # UTC is sufficient for interval comparisons; local night is validated separately.
        result.append((dt, float(item.attrib["lat"]), float(item.attrib["lon"])))
    return result


def haversine_m(lat_a, lon_a, lat_b, lon_b):
    radius = 6371008.8
    lat_a, lon_a, lat_b, lon_b = map(math.radians, (lat_a, lon_a, lat_b, lon_b))
    dlat, dlon = lat_b - lat_a, lon_b - lon_a
    h = math.sin(dlat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(h)))


def csv_rows(relative):
    path = ROOT / relative
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class October2026EvidenceTests(unittest.TestCase):
    def test_exact_hash_and_point_count_for_every_night(self):
        for night in NIGHTS:
            with self.subTest(night=night):
                payload, manifest = raw_gpx(night)
                track = points(payload)
                self.assertEqual(len(track), manifest["trackpoint_count"])
                self.assertGreater(len(track), 0)

    def test_habu_events_match_gpx_100m_10min(self):
        for night in NIGHTS:
            with self.subTest(night=night):
                payload, _ = raw_gpx(night)
                track = points(payload)
                events = csv_rows(f"data/processed/capture_events/2026/{night}.csv")
                events += csv_rows(f"data/processed/habu_reactions/2026/{night}.csv")
                for event in events:
                    timestamp = datetime.fromisoformat(event["event_time_local"])
                    latitude, longitude = float(event["latitude"]), float(event["longitude"])
                    nearby = (
                        haversine_m(latitude, longitude, lat, lon)
                        for t, lat, lon in track if abs((t - timestamp).total_seconds()) <= 600
                    )
                    self.assertTrue(any(d <= 100 for d in nearby), event["event_id"])

    def test_capture_and_reaction_classes_are_disjoint(self):
        cap14 = csv_rows("data/processed/capture_events/2026/2026-10-14.csv")
        cap15 = csv_rows("data/processed/capture_events/2026/2026-10-15.csv")
        roadkill = csv_rows("data/processed/habu_reactions/2026/2026-10-08.csv")
        self.assertEqual(sum(int(r["event_count"]) for r in cap14), 3)
        self.assertEqual(sum(int(r["event_count"]) for r in cap15), 3)
        self.assertEqual(sum(int(r["event_count"]) for r in roadkill), 1)
        self.assertTrue(all(r["event_type"] == "capture" for r in cap14 + cap15))
        self.assertTrue(all(r["event_type"] == "roadkill" for r in roadkill))
        self.assertEqual(set(r["event_id"] for r in cap14 + cap15) & set(r["event_id"] for r in roadkill), set())

    def test_after_midnight_capture_belongs_to_oct14_night(self):
        caps = csv_rows("data/processed/capture_events/2026/2026-10-14.csv")
        midnight = [r for r in caps if r["event_time_local"].startswith("2026-10-15T00:20")]
        self.assertEqual(len(midnight), 1)
        self.assertEqual(midnight[0]["operational_date"], "2026-10-14")
        self.assertEqual(operational_night(datetime.fromisoformat(midnight[0]["event_time_local"])), "2026-10-14")

    def test_no_false_original_freeze_for_recovered_candidates(self):
        for night in NIGHTS:
            candidate = json.loads((ROOT / "evidence/prediction_recovery_candidates" / (night + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(candidate["strict_official_score_eligible"], False)
            self.assertEqual(candidate["original_freeze_found"], False)
            self.assertEqual(candidate["do_not_score_as_original"], True)
            self.assertFalse((ROOT / "predictions/original" / night / "P0/prediction.json").exists())


if __name__ == "__main__":
    unittest.main()
