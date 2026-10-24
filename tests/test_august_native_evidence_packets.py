"""Real user Library-original byte verification and scientific review-packet restrictions."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_august_native_capture_original import (
    LIBRARY_RAW_SHA256,LIBRARY_RAW_BYTES,LIBRARY_RAW_LINES,
    SOURCE,SourceProvenanceError,audit_original
)
from build_august_source_evidence_packets import (
    BLOCKERS,PacketAuditError,_build_groups,build_packets
)

class NativeCaptureByteSourceTests(unittest.TestCase):
    def test_exact_raw_native_august_txt_and_all_daily_capture_counts(self):
        summary,events=audit_original(ROOT)
        lib=summary["library_native_original"]
        self.assertEqual(lib["raw_file_sha256"],LIBRARY_RAW_SHA256)
        self.assertEqual(lib["raw_file_size_bytes"],LIBRARY_RAW_BYTES)
        self.assertEqual(lib["raw_utf8_line_count"],LIBRARY_RAW_LINES)
        self.assertTrue(summary["repository_source"]["byte_identical_to_library_native"])
        self.assertFalse(lib["field_device_cryptographic_signature_verified"])
        self.assertEqual(summary["native_capture_event_statements"],46)
        self.assertEqual(summary["native_capture_statement_quantity_sum"],47)
        self.assertEqual(summary["august_capture_nights"],17)
        self.assertEqual(summary["owner_confirmed_august_count"],47)
        self.assertEqual(len(summary["day_counts"]),17)
        self.assertTrue(summary["all_daily_capture_statement_quantities_match_owner_dashboard"])
        self.assertEqual(len(events),46)
        self.assertEqual(len({e["source_block_sha256"] for e in events}),46)
        self.assertTrue(any(e["explicit_two_quantity"] and e["night"]=="2026-08-19" for e in events))
        self.assertEqual(sum(e["captured_quantity_candidate"] for e in events),47)
        self.assertEqual(summary["aug31_two_capture_event_blocks"],2)
        self.assertTrue(8000<summary["aug31_source_record_separation_m"]<10000)
        self.assertFalse(summary["aug31_distinct_physical_individual_ids_verified"])
        self.assertFalse(summary["canonical_individual_ids_verified"])
        self.assertEqual(summary["formal_positive_training_rows"],0)
        self.assertEqual(summary["formal_negative_training_rows"],0)

    def test_native_byte_sha_tamper_rejected_not_recovered_by_monthly_dashboard(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            log=root/SOURCE;log.parent.mkdir(parents=True,exist_ok=True)
            log.write_bytes((ROOT/SOURCE).read_bytes()+b"\n")
            with self.assertRaisesRegex(SourceProvenanceError,"byte SHA or byte count"):
                audit_original(root)

    def test_owner_monthly_count_does_not_override_missing_raw_event_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            log=root/SOURCE;log.parent.mkdir(parents=True,exist_ok=True)
            log.write_bytes((ROOT/SOURCE).read_bytes())
            dashboard=root/"dashboard/baseline_2026.json"
            dashboard.parent.mkdir(parents=True,exist_ok=True)
            b=json.loads((ROOT/"dashboard/baseline_2026.json").read_text())
            b["owner_confirmed_monthly_counts"]["2026-08"]["count"]=48
            dashboard.write_text(json.dumps(b,ensure_ascii=False))
            with self.assertRaisesRegex(SourceProvenanceError,"Owner-confirmed August 47"):
                audit_original(root)

class GroupUnitTests(unittest.TestCase):
    def make_row(self,number,x,y,night="2026-08-31",window="2026-08-31T21:10:00+09:00",way=10):
        return {"candidate_id":str(number),"night":night,"cell_x":x,"cell_y":y,
                "window_start_jst":window,"osm_way_candidate":way,
                "quality_gpx_samples":7,"osm_road_nearby_samples":6,
                "observation":"UNKNOWN","label":None}

    def test_no_invented_connection_across_gap_window_or_way(self):
        rows=[self.make_row("a",100,100),
              self.make_row("b",100,101),
              self.make_row("c",104,101),
              self.make_row("d",100,102,way=11),
              self.make_row("e",100,101,window="2026-08-31T21:20:00+09:00")]
        grouped=_build_groups(rows)
        self.assertEqual(sorted(g["spatially_adjacent_sampled_cells"] for g in grouped),[1,1,1,2])
        self.assertTrue(all(g["spatial_grouping_only_not_proven_driven_route"] for g in grouped))
        self.assertTrue(all(g["promoted_model_negative_count"]==0 for g in grouped))
        with self.assertRaisesRegex(PacketAuditError,"Duplicate sampled cells"):
            _build_groups([self.make_row("a",100,100),self.make_row("b",100,100)])

class RealAugustEvidencePacketsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result,cls.groups,cls.cells=build_packets(ROOT)

    def test_real_data_3491_candidate_cells_grouped_once(self):
        r=self.result
        self.assertEqual(r["owner_monthly_capture_total"],47)
        self.assertEqual(r["august_12_actual_gpx_nights"],12)
        self.assertEqual(r["sampled_100m_10min_total"],8965)
        self.assertEqual(r["road_gpx_match_samples"],205707)
        self.assertEqual(r["noncapture_review_candidate_cells"],3491)
        self.assertEqual(len(self.cells),3491)
        self.assertEqual(len({c["candidate_id"] for c in self.cells}),3491)
        self.assertGreater(len(self.groups),0)
        self.assertLessEqual(len(self.groups),len(self.cells))
        self.assertEqual(r["review_packets_grouped_by_single_window_osm_way_and_spatial_adjacency"],len(self.groups))
        self.assertEqual(sum(g["spatially_adjacent_sampled_cells"] for g in self.groups),3491)
        self.assertEqual(sum(n["review_candidate_cells"] for n in r["night_summaries"]),3491)
        self.assertEqual({n["night"] for n in r["night_summaries"]}, {
            "2026-08-12","2026-08-13","2026-08-15","2026-08-17",
            "2026-08-19","2026-08-21","2026-08-23","2026-08-24",
            "2026-08-27","2026-08-28","2026-08-29","2026-08-31"})
        self.assertTrue(all(n["review_candidate_cells"]==0 for n in r["night_summaries"]
                            if n["night"] in ("2026-08-12","2026-08-13","2026-08-29")))
        self.assertTrue(any(n["review_candidate_cells"]>0 for n in r["night_summaries"]))

    def test_gating_source_authentication_vs_actual_search(self):
        r=self.result
        self.assertTrue(r["source_provenance"]["native_file_bytes_verified"])
        self.assertEqual(r["source_provenance"]["source_event_statements"],46)
        self.assertEqual(r["source_provenance"]["source_statement_capture_quantity"],47)
        self.assertFalse(r["source_provenance"]["canonical_individual_ids_independently_verified"])
        self.assertEqual(set(r["review_blockers"]),set(BLOCKERS))
        self.assertFalse(r["training_allowed"])
        self.assertEqual(r["formally_eligible_non_capture_labels"],0)
        self.assertEqual(r["formally_eligible_capture_labels"],0)
        self.assertEqual(r["scientifically_certified_road_search_segments"],0)
        self.assertTrue(all(c["observation"]=="UNKNOWN" and c["label"] is None for c in self.cells))
        self.assertTrue(all(not c["field_search_road_attested"] and
                            not c["complete_night_outcome_attested"] for c in self.cells))
        self.assertTrue(all(not g["spatial_grouping_only_not_proven_driven_route"] is False for g in self.groups))

if __name__=="__main__":
    unittest.main()
