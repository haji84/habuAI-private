"""Synthetic source-closure declarations never certify actual Habu observations."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from master_contracts import canonical_bytes, digest
from prospective_inputs import ProspectiveReadContext, READINESS_FIELDS
import test_training_corpus as corpus_fixtures
from test_g0_forecast_contract import base_ref, definition_hash

READY = "2026-10-01T14:00:00+09:00"


class TrainingSourceContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = corpus_fixtures.AuditedTrainingTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        code = base_ref(self.root, "src/synthetic_static.py", b"# synthetic source only\n")
        code.update(readiness={key: READY for key in READINESS_FIELDS}, usable_at=READY)
        definition = "Static road length in metres in a declared 100m cell"
        self.features = [dict(name="road_length_m", units="m", version="1", definition=definition,
            definition_sha256=hashlib.sha256(definition.encode()).hexdigest(), code_ref=code,
            deployment="static_predictor", required_source_ids=["road-source"])]
        self.build_manifest()

    def bound(self, ref):
        return dict(ref=ref, readiness={key: READY for key in READINESS_FIELDS}, usable_at=READY)

    def build_manifest(self):
        f = self.fixture
        sources = f.corpus["source_manifest"]
        paths = {source["path"]: ("road-source" if source["path"] == "features/road-source.txt" else "source-" + str(index))
                 for index, source in enumerate(sources)}
        nodes = []
        for source in sources:
            relative = source["path"]
            raw = (self.root / relative).read_bytes()
            parents = []
            if source["role"] in {"active_search", "complete_outcome"}:
                parents = [paths[ref["path"]] for ref in json.loads(raw)["basis_source_refs"]]
            readiness = {key: READY for key in READINESS_FIELDS}
            readiness["source_received_at"] = source["received_at"]
            nodes.append(dict(id=paths[relative], ref=dict(path=relative, sha256=source["sha256"], size_bytes=len(raw)),
                source_role=source["role"], source_kind="DERIVED" if parents else "RAW",
                parents=parents, readiness=readiness, usable_at=READY))
        corpus_raw = (self.root / f.path).read_bytes()
        policy_path = "protocols/development/g0-policy-v1.json"
        policy = base_ref(self.root, policy_path, (ROOT / policy_path).read_bytes())
        self.validity = dict(schema_version="habu-g0-training-validity-v1", corpus_sha256=f.sha,
            feature_definition_sha256=definition_hash(self.features), rows={})
        for row in f.rows:
            start = datetime.fromisoformat(row["window_start_jst"])
            self.validity["rows"][row["row_id"]] = {name: dict(
                valid_time=dict(start=start.isoformat(), end=(start + timedelta(minutes=10)).isoformat()),
                source_ids=[paths[path] for path in row["feature_source_refs"][name]])
                for name in row["features"]}
        validity_ref = base_ref(self.root, "features/synthetic-training-validity.json", canonical_bytes(self.validity))
        self.manifest = dict(schema_version="habu-g0-training-source-contract-v1", kind="TRAIN_ONLY_SOURCE_CLOSURE",
            corpus=self.bound(dict(path=f.path, sha256=f.sha, size_bytes=len(corpus_raw))),
            policy=self.bound(policy), row_validity=self.bound(validity_ref), features=copy.deepcopy(self.features),
            feature_definition_sha256=definition_hash(self.features), source_nodes=nodes,
            readiness={key: READY for key in READINESS_FIELDS}, usable_at=READY)
        self.publish()

    def publish(self):
        self.ref = base_ref(self.root, "protocols/development/synthetic-training.json", canonical_bytes(self.manifest) + b"\n")

    def call(self, **options):
        from g0_training_source_contract import select_g0_training_rows
        return select_g0_training_rows(self.root, self.ref, "2026-10-20", "2026-10-19T19:00:00+09:00",
            "2026-10-20T18:00:00+09:00", expected_feature_definition_sha256=definition_hash(self.features),
            **options)

    def test_complete_declared_closure_calls_same_source_bound_selector(self):
        result = self.call()
        self.assertEqual(result["selection"], self.fixture.select())
        receipt = result["receipt"]
        self.assertEqual(receipt["source_authentication"], "NOT_ATTESTED")
        self.assertFalse(receipt["scientific_fit_authorized"])
        self.assertFalse(receipt["production_authorized"])
        self.assertEqual(receipt["feature_definition_sha256"], definition_hash(self.features))
        self.assertNotEqual(receipt["feature_definition_sha256"], receipt["legacy_feature_names_sha256"])

    def test_missing_four_readiness_and_later_unused_sources_are_g0_blocks(self):
        from g0_training_source_contract import G0TrainingInputBlocked
        del self.manifest["source_nodes"][0]["readiness"]["audited_at"]
        self.publish()
        with self.assertRaises(G0TrainingInputBlocked):
            self.call()
        self.fixture.add_development_holdout()
        self.assertEqual(self.fixture.select()["status"], "DEVELOPMENT_TRAINING_ELIGIBLE")
        self.build_manifest()
        with self.assertRaises(G0TrainingInputBlocked):
            self.call()

    def test_source_hash_role_and_receipt_received_time_must_match_actual_corpus(self):
        for field, value in (("source_role", "feature"), ("received_at", "2026-10-01T00:00:00+09:00"), ("sha256", "f" * 64)):
            self.build_manifest()
            source = self.manifest["source_nodes"][0]
            if field == "source_role":
                source[field] = value
            elif field == "received_at":
                source["readiness"]["source_received_at"] = value
            else:
                source["ref"][field] = value
            self.publish()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.call()

    def test_parent_audit_readiness_can_be_later_than_derived_artifact_own_times(self):
        node = next(node for node in self.manifest["source_nodes"] if node["source_role"] == "active_search")
        for name in READINESS_FIELDS - {"source_received_at"}:
            node["readiness"][name] = "2026-09-30T13:00:00+09:00"
        self.publish()
        self.assertEqual(self.call()["selection"], self.fixture.select())

    def test_omitted_source_or_missing_derived_parent_cannot_be_blessed_by_rehash(self):
        self.manifest["source_nodes"].pop()
        self.publish()
        with self.assertRaises(ValueError):
            self.call()
        self.build_manifest()
        node = next(node for node in self.manifest["source_nodes"] if node["source_role"] == "active_search")
        node["parents"] = []
        self.publish()
        with self.assertRaises(ValueError):
            self.call()

    def test_feature_definition_units_and_code_readiness_are_bound_before_fit(self):
        self.manifest["features"][0]["units"] = "km"
        self.publish()
        with self.assertRaises(ValueError):
            self.call()
        self.build_manifest()
        self.manifest["features"][0]["code_ref"]["readiness"]["audited_at"] = "2026-10-20T18:00:00+09:00"
        self.publish()
        with self.assertRaises(ValueError):
            self.call()

    def test_sealed_reference_is_rejected_before_any_target_payload_read(self):
        self.manifest["source_nodes"][-1]["ref"]["path"] = "sealed/confirmation/unread.json"
        self.publish()
        actual_open = Path.open
        def guarded(path, *args, **kwargs):
            if "sealed" in path.parts:
                raise AssertionError("sealed payload was opened")
            return actual_open(path, *args, **kwargs)
        with patch.object(Path, "open", new=guarded), self.assertRaises(ValueError):
            self.call()

    def test_per_row_physical_validity_and_source_role_binding_are_required(self):
        for mode in ("missing", "short", "label_source"):
            self.build_manifest()
            row = self.validity["rows"][self.fixture.rows[0]["row_id"]]
            if mode == "missing":
                self.validity["rows"].pop(self.fixture.rows[0]["row_id"])
            elif mode == "short":
                row["road_length_m"]["valid_time"]["end"] = self.fixture.rows[0]["window_start_jst"]
            else:
                row["road_length_m"]["source_ids"] = [self.manifest["source_nodes"][0]["id"]]
            self.manifest["row_validity"]["ref"] = base_ref(self.root,
                "features/synthetic-training-validity.json", canonical_bytes(self.validity))
            self.publish()
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.call()

    def test_registered_required_source_cannot_be_missing_even_with_rebound_definition(self):
        self.features[0]["required_source_ids"] = ["missing-registered-provider"]
        self.build_manifest()
        with self.assertRaises(ValueError):
            self.call()

    def test_sealed_code_ref_is_rejected_before_its_bytes_are_opened(self):
        ref = base_ref(self.root, "src/sealed/confirmation/unread.py", b"sealed fixture must remain unread")
        self.features[0]["code_ref"] = dict(ref, readiness={key: READY for key in READINESS_FIELDS}, usable_at=READY)
        self.build_manifest()
        actual_open = Path.open
        opens = []
        def observe(path, *args, **kwargs):
            if "sealed" in path.parts:
                opens.append(path)
            return actual_open(path, *args, **kwargs)
        error = None
        with patch.object(Path, "open", new=observe):
            try:
                self.call()
            except ValueError as exc:
                error = exc
        self.assertEqual(opens, [])
        self.assertIsNotNone(error)

    def test_label_bytes_cannot_be_redeclared_as_a_raw_feature_at_a_new_path(self):
        from g0_training_source_contract import G0TrainingInputBlocked
        raw = (self.root / "evidence/source_receipt.txt").read_bytes()
        (self.root / "features/road-source.txt").write_bytes(raw)
        for source in self.fixture.corpus["source_manifest"]:
            if source["path"] == "features/road-source.txt":
                source["sha256"] = hashlib.sha256(raw).hexdigest()
        self.fixture.publish()
        self.build_manifest()
        with self.assertRaises(G0TrainingInputBlocked):
            self.call()

    def test_lineage_capacity_is_checked_before_shared_raw_sets_amplify(self):
        import g0_training_source_contract as gate
        from prospective_inputs import InputCapacityError
        for index in range(2):
            self.fixture.add_source(f"features/derived-extra-{index}.txt", f"synthetic derived {index}".encode(),
                "2026-09-30T12:00:00+09:00", "feature")
        self.fixture.publish()
        self.build_manifest()
        for node in self.manifest["source_nodes"]:
            if "derived-extra-" in node["ref"]["path"]:
                node.update(source_kind="DERIVED", parents=["road-source"])
        self.publish()
        with patch.object(gate, "MAX_LINEAGE_MEMBERSHIPS", 2), self.assertRaises(InputCapacityError):
            self.call()

    def test_scope_basis_bad_path_type_is_invalid_evidence(self):
        source = next(item for item in self.fixture.corpus["source_manifest"] if item["role"] == "active_search")
        target = self.root / source["path"]
        payload = json.loads(target.read_bytes())
        payload["basis_source_refs"][0]["path"] = []
        raw = canonical_bytes(payload)
        target.write_bytes(raw)
        source["sha256"] = hashlib.sha256(raw).hexdigest()
        self.fixture.publish()
        node = next(item for item in self.manifest["source_nodes"] if item["ref"]["path"] == source["path"])
        node["ref"].update(sha256=source["sha256"], size_bytes=len(raw))
        self.manifest["corpus"]["ref"] = base_ref(self.root, self.fixture.path,
            (self.root / self.fixture.path).read_bytes())
        self.validity["corpus_sha256"] = self.fixture.sha
        self.manifest["row_validity"]["ref"] = base_ref(self.root,
            "features/synthetic-training-validity.json", canonical_bytes(self.validity))
        self.publish()
        with self.assertRaises(ValueError):
            self.call()

    def test_shared_deadline_and_source_mutation_release_no_selection(self):
        with patch("prospective_inputs.monotonic", return_value=0):
            context = ProspectiveReadContext(30, 1000000)
        with patch("prospective_inputs.monotonic", return_value=31), self.assertRaises(TimeoutError):
            self.call(_read_context=context)
        (self.root / "features/road-source.txt").write_bytes(b"source changed")
        with self.assertRaises(ValueError):
            self.call()


if __name__ == "__main__":
    unittest.main()
