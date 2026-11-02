"""Hermetic contracts for the GitHub-hosted reviewer (no model or network needed)."""
import json
from io import BytesIO
import os
import tempfile
import unittest
from unittest.mock import patch

import review


class ReviewContractTests(unittest.TestCase):
    def test_model_endpoint_is_local_and_code_selection_excludes_raw_gps(self):
        self.assertEqual(review.OLLAMA_URL, "http://127.0.0.1:11434/api/chat")
        self.assertNotIn(".gpx", review.SOURCE_SUFFIXES)
        self.assertNotIn(".jsonl", review.SOURCE_SUFFIXES)
        self.assertNotIn(".ndjson", review.SOURCE_SUFFIXES)

    def test_finding_is_bound_to_one_file_and_valid_positive_line(self):
        rows = review.parse_findings(json.dumps({"findings": [
            {"path": "mobile/a.kt", "line": 7, "problem": "This accepts fixes before start",
             "impact": "Track gets stale GPS points"},
            {"path": "elsewhere/a.kt", "line": 3, "problem": "Cross-file hallucination",
             "impact": "Should be rejected"},
            {"path": "mobile/a.kt", "line": -1, "problem": "Invalid negative line",
             "impact": "Should be rejected"},
            {"path": "mobile/a.kt", "line": 2, "problem": "tiny", "impact": "short"}
        ]}), "mobile/a.kt")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["line"], 7)

    def test_structured_model_schema_requires_exact_segment_id(self):
        seen = []

        def fake_urlopen(req, timeout):
            seen.append(json.loads(req.data))
            return BytesIO(json.dumps({
                "model": review.MODEL,
                "done": True,
                "prompt_eval_count": 42,
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"segment_id": "part-001", "findings": []}),
                },
            }).encode("utf-8"))

        with patch.object(review.urllib.request, "urlopen", side_effect=fake_urlopen):
            actual = review.ask_model("mobile/a.kt", "OWNED DIFF", segment_id="part-001")
        self.assertEqual(json.loads(actual)["segment_id"], "part-001")
        schema = seen[0]["format"]
        self.assertEqual(schema["properties"]["segment_id"]["enum"], ["part-001"])
        self.assertEqual(set(schema["required"]), {"segment_id", "findings"})
        self.assertEqual(seen[0]["stream"], False)

    def test_model_receipt_requires_done_and_prompt_evaluation(self):
        good = {
            "model": review.MODEL, "done": True, "prompt_eval_count": 42,
            "message": {"role": "assistant", "content": '{"findings":[]}'},
        }
        cases = [
            dict(good, done=False),
            dict(good, prompt_eval_count=0),
            dict(good, model="unrequested-model"),
            dict(good, message={"role": "user", "content": '{"findings":[]}' }),
        ]
        for case in cases:
            with self.subTest(case=case):
                with patch.object(review.urllib.request, "urlopen",
                                  return_value=BytesIO(json.dumps(case).encode("utf-8"))):
                    with self.assertRaises(ValueError):
                        review.ask_model("mobile/a.kt", "OWNED DIFF", segment_id="part-001")

    def test_segment_acknowledgement_must_match_exactly(self):
        valid = json.dumps({"segment_id": "sha-part-001", "findings": []})
        self.assertEqual(
            review.parse_findings(valid, "mobile/a.kt",
                                  expected_segment_id="sha-part-001"), [])
        for invalid in (
            json.dumps({"segment_id": "sha-part-002", "findings": []}),
            json.dumps({"findings": []}),
            json.dumps({"segment_id": "", "findings": []}),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "acknowledge"):
                    review.parse_findings(invalid, "mobile/a.kt",
                                          expected_segment_id="sha-part-001")

    def test_review_segment_retries_wrong_ack_before_counting_it(self):
        responses = [
            json.dumps({"segment_id": "wrong", "findings": []}),
            json.dumps({"segment_id": "correct-part", "findings": []}),
        ]
        with patch.object(review, "ask_model", side_effect=responses) as model:
            result = review.review_segment(
                "mobile/a.kt", "FIRST segment", "correct-part")
        self.assertEqual(result, [])
        self.assertEqual(model.call_count, 2)
        self.assertEqual(model.call_args.kwargs["segment_id"], "correct-part")

    def test_review_segment_retries_timeout_without_fake_coverage(self):
        responses = [
            TimeoutError("local model timeout"),
            json.dumps({"segment_id": "correct-part", "findings": []}),
        ]
        with patch.object(review, "ask_model", side_effect=responses) as model:
            self.assertEqual(review.review_segment(
                "mobile/a.kt", "MIDDLE segment", "correct-part"), [])
        self.assertEqual(model.call_count, 2)

    def test_review_segment_fails_closed_after_unacknowledged_tail(self):
        bad = json.dumps({"segment_id": "out-of-order-part", "findings": []})
        with patch.object(review, "ask_model", return_value=bad) as model:
            with self.assertRaisesRegex(ValueError, "unverified"):
                review.review_segment("mobile/a.kt", "LAST segment", "tail-part")
        self.assertEqual(model.call_count, 2)

    def test_fallback_losslessly_verifies_every_child_before_parent(self):
        owned = "diff --git a/a b/a\n" + ("+first " * 150) + "\n" + ("+last " * 150)
        # Repeated malformed original response must not count as review.
        expected = review.split_patch(owned, limit=max(256, len(owned) // 2))
        seen = []
        def model(path, prompt, model=review.MODEL, segment_id=None):
            seen.append((segment_id, prompt))
            if segment_id == "whole-root":
                return "NOT JSON"
            return json.dumps({"segment_id": segment_id, "findings": []})
        with patch.object(review, "ask_model", side_effect=model):
            result = review.review_segment(
                "mobile/a.kt", "FULL OWNED DIFF", "whole-root", owned=owned)
        self.assertEqual(result, [])
        self.assertEqual(len(seen), 2 + len(expected))
        for part, (_, prompt) in zip(expected, seen[2:]):
            self.assertIn("OWNED DIFF SEGMENT:\n" + part + "\n", prompt)
        self.assertEqual("".join(expected), owned)

    def test_fallback_never_passes_when_a_child_remains_invalid(self):
        owned = "+observed-data" * 150
        def model(path, prompt, model=review.MODEL, segment_id=None):
            return "NOT JSON"
        with patch.object(review, "ask_model", side_effect=model):
            with self.assertRaisesRegex(ValueError, "unverified"):
                review.review_segment(
                    "mobile/a.kt", "FULL OWNED DIFF", "whole-root", owned=owned)

    def test_ollama_output_limit_is_not_counted_as_verified_segment(self):
        reply = {
            "model": review.MODEL, "done": True, "done_reason": "length",
            "prompt_eval_count": 100,
            "message": {"role": "assistant", "content": '{"findings":['},
        }
        with patch.object(review.urllib.request, "urlopen",
                          return_value=BytesIO(json.dumps(reply).encode("utf-8"))):
            with self.assertRaisesRegex(ValueError, "complete answer"):
                review.ask_model("mobile/a.kt", "OWNED DIFF", segment_id="part-001")

    def test_generation_limited_short_tail_keeps_every_child_and_tail_finding(self):
        finding = {"path": "mobile/a.kt", "line": 12,
                   "problem": "A concrete defect occurs in the final child.",
                   "impact": "The final source section must be reviewed."}
        cases = [
            ("A" * 256 + "Z", ["A" * 256, "Z"]),
            ("A" * 256 + "B" * 212 + "Z", ["A" * 256, "B" * 212 + "Z"]),
            ("A" * 256 + "C" * 254 + "Z", ["A" * 256, "C" * 254 + "Z"]),
        ]
        for owned, expected_children in cases:
            with self.subTest(length=len(owned)):
                children = []

                def local_response(req, timeout):
                    payload = json.loads(req.data)
                    segment_id = payload["format"]["properties"]["segment_id"]["enum"][0]
                    limited = segment_id == "short-root"
                    if limited:
                        content = '{"findings":['
                    else:
                        prompt = payload["messages"][-1]["content"]
                        child = prompt.split("OWNED DIFF SEGMENT:\n", 1)[1].split(
                            "\nPREVIOUS CONTEXT ONLY:\n", 1)[0]
                        children.append(child)
                        content = json.dumps({
                            "segment_id": segment_id,
                            "findings": [finding] if child.endswith("Z") else [],
                        })
                    return BytesIO(json.dumps({
                        "model": review.MODEL, "done": True,
                        "done_reason": "length" if limited else "stop",
                        "prompt_eval_count": 100,
                        "message": {"role": "assistant", "content": content},
                    }).encode("utf-8"))

                with patch.object(review.urllib.request, "urlopen",
                                  side_effect=local_response):
                    try:
                        result = review.review_segment(
                            "mobile/a.kt", "ROOT PROMPT", "short-root", owned=owned)
                    except ValueError:
                        self.fail("A fully acknowledged short tail remained unverified")
                self.assertEqual(children, expected_children)
                self.assertEqual("".join(children), owned)
                self.assertEqual(result, [finding])

    def test_short_tail_failed_final_child_keeps_parent_unverified(self):
        owned = "A" * 256 + "B" * 212 + "Z"

        def model(path, prompt, model=review.MODEL, segment_id=None):
            if segment_id == "short-root":
                raise ValueError("Inference ended before a complete answer")
            if "OWNED DIFF SEGMENT:\n" + "B" * 212 + "Z\n" in prompt:
                return json.dumps({"segment_id": "wrong-child", "findings": []})
            return json.dumps({"segment_id": segment_id, "findings": []})

        with patch.object(review, "ask_model", side_effect=model):
            with self.assertRaisesRegex(ValueError, "unverified"):
                review.review_segment(
                    "mobile/a.kt", "ROOT PROMPT", "short-root", owned=owned)

    def test_short_tail_respects_minimum_size_and_subdivision_depth(self):
        for size, depth in [(256, 0), (469, review.MAX_SUBDIVISION_DEPTH)]:
            with self.subTest(size=size, depth=depth):
                with patch.object(review, "ask_model", side_effect=ValueError(
                        "Inference ended before a complete answer")):
                    with self.assertRaisesRegex(ValueError, "unverified"):
                        review.review_segment(
                            "mobile/a.kt", "ROOT PROMPT", "short-root",
                            owned="X" * size, depth=depth)

    def test_qualification_requires_actual_candidate_finding(self):
        self.assertFalse(review.qualification_passes([]))
        self.assertTrue(review.qualification_passes([
            {"problem": "The grace period allows fixes before tracking starts.",
             "impact": "Old GPS points enter a new exploration session."}
        ]))
        self.assertFalse(review.qualification_passes([
            {"problem": "Wrong capitalization of a variable",
             "impact": "Not a confirmed GPS session bug."}
        ]))

    def test_malformed_model_output_must_not_count_as_pass(self):
        for value in ("not-json", "{}", '{"findings":null}', "[]"):
            with self.subTest(value=value):
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    review.parse_findings(value, "mobile/a.kt")

    def test_exact_sha_and_file_allowlist_and_priority(self):
        base = "a" * 40
        head = "b" * 40

        def git_mock(*args):
            if args[0] == "rev-parse":
                return head
            if args[0] == "merge-base":
                return base
            if args[0] == "diff" and "--name-only" in args:
                return "\n".join([
                    "dashboard/field-app.js",
                    "scripts/import_owner_batch.py",
                    "scripts/build_capture_dashboard.py",
                    "dashboard/intake.html",
                    "tests/test_field_offline.py",
                    "dashboard/raw/secret.py",
                    "dashboard/private/confidential.js",
                    "dashboard/data/locations.js",
                    "dashboard/dist/generated.js",
                    "scripts/private/hidden.py",
                    "scripts/raw/live.py",
                    "tests/data/cases.js",
                    "dashboard/private.gpx",
                    "dashboard/records.json",
                    "mobile/LocationTrackingService.kt",
                    "docs/strategy.md",
                    ".env",
                ])
            raise AssertionError(args)

        with patch.object(review, "git", side_effect=git_mock):
            selected = review.source_paths(base, head)
        self.assertEqual(len(selected), 5)
        self.assertEqual(selected[0], "scripts/import_owner_batch.py")
        self.assertTrue(any(x.endswith("intake.html") for x in selected))
        self.assertTrue(any(x.endswith("field-app.js") for x in selected))
        self.assertFalse(any(x.startswith(review.DENY_PREFIXES) for x in selected))
        self.assertFalse(any(x.endswith((".json", ".gpx", ".kt")) for x in selected))

    def test_pr136_advisory_cannot_read_private_or_mobile_directories(self):
        self.assertEqual(review.SOURCE_DIRS, ("dashboard/", "scripts/", "tests/"))
        self.assertEqual(review.MODEL, "qwen2.5-coder:1.5b")
        self.assertNotIn(".json", review.SOURCE_SUFFIXES)
        self.assertNotIn("mobile/", review.SOURCE_DIRS)
        self.assertIn("dashboard/private/", review.DENY_PREFIXES)
        self.assertIn("dashboard/raw/", review.DENY_PREFIXES)
        self.assertIn("scripts/private/", review.DENY_PREFIXES)

    def test_refuses_unknown_commit_and_different_checked_out_head(self):
        with self.assertRaises(ValueError):
            review.source_paths("bad", "b" * 40)
        with patch.object(review, "git", return_value="a" * 40):
            with self.assertRaisesRegex(ValueError, "HEAD"):
                review.source_paths("a" * 40, "b" * 40)

    def test_long_patch_preserves_tail_and_start_without_truncation(self):
        # Distinct beginnings and endings must survive the full chunk journey.
        patch = ("diff --git a/mobile/a.kt b/mobile/a.kt\\n"
                 "@@ -1,0 +1,800 @@\\n" +
                 "".join(f"+observed_change_{n:04d}: used in review\\n"
                         for n in range(800)) +
                 "+END_SENTINEL_SHOULD_NOT_BE_LOST")
        chunks = review.split_patch(patch, limit=900)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(chunks[0].startswith("diff --git"))
        self.assertTrue(chunks[-1].endswith("END_SENTINEL_SHOULD_NOT_BE_LOST"))
        self.assertTrue(all(len(part) <= 900 for part in chunks))
        self.assertEqual("".join(chunks), patch)

    def test_chunk_long_single_line_is_never_discarded(self):
        # Even pathological generated-code lines need complete coverage.
        patch = "BEGIN" + ("X" * 9500) + "END"
        chunks = review.split_patch(patch, limit=1000)
        self.assertEqual("".join(chunks), patch)
        self.assertEqual(len(chunks), 10)
        self.assertEqual(chunks[0][:5], "BEGIN")
        self.assertEqual(chunks[-1][-3:], "END")
        self.assertTrue(all(0 < len(part) <= 1000 for part in chunks))

    def test_review_first_middle_last_including_one_chunk_files(self):
        groups = [
            ("mobile/a.kt", ["A-HEAD", "A-MIDDLE", "A-TAIL"]),
            ("tests/small.py", ["SINGLE-HEAD"]),
            ("mobile/b.swift", ["B-HEAD", "B-TAIL"]),
        ]
        ordered = review.review_order(groups)
        self.assertEqual([part for _, _, _, part in ordered],
                         ["A-HEAD", "A-MIDDLE", "A-TAIL",
                          "SINGLE-HEAD", "B-HEAD", "B-TAIL"])
        self.assertEqual({path for path, _, _, _ in ordered},
                         {path for path, _ in groups})
        self.assertEqual(len(ordered), 6)

    def test_git_diff_keeps_trailing_whitespace(self):
        # The very last diff byte must survive before chunking.
        class Completed:
            stdout = "diff body with whitespace  \n\n"
        with patch.object(review.subprocess, "run", return_value=Completed()):
            self.assertEqual(review.git("diff", "--no-ext-diff", "x"),
                             "diff body with whitespace  \n\n")
            self.assertEqual(review.git("rev-parse", "HEAD"),
                             "diff body with whitespace")

    def test_invalid_or_empty_patch_fails_closed(self):
        for bad_limit in (0, 15, 255):
            with self.assertRaises(ValueError):
                review.split_patch("test", limit=bad_limit)
        with self.assertRaises(ValueError):
            review.split_patch("")
        with self.assertRaises(ValueError):
            review.review_order([("mobile/missing.kt", [])])

    def test_summary_sanitizes_untrusted_model_text(self):
        result = review.safe_md("<img src=x onerror=alert(1)>| surprise\nnext")
        self.assertNotIn("<img", result)
        self.assertNotIn("|", result)
        self.assertNotIn("\n", result)

    def test_summary_is_local_and_does_not_require_gh_token(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "summary.md")
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": output}):
                review.write_summary(["STATUS: HOLD", "No merge or upload"])
            with open(output, encoding="utf-8") as handle:
                result = handle.read()
        self.assertIn("STATUS: HOLD", result)


if __name__ == "__main__":
    unittest.main()
