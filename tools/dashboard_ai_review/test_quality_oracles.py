"""Behavioral oracle for the six fixed synthetic review-calibration cases.

The verdict labels stay unchanged. This independently checks what the trusted
fixture actually does, so calibration does not grade imaginary requirements.
Only fixed in-repository synthetic snippets are executed, never model output,
private GPS files, or arbitrary PR-source code.
"""
from __future__ import annotations

from html.parser import HTMLParser
import json
import shutil
import subprocess
import unittest

import quality


CASES = {case["name"]: case for case in quality.CASES}


def source(name: str) -> str:
    return CASES[name]["source"]


class HtmlStructure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headers_started = 0
        self.headers_ended = 0
        self.button_names = []

    def handle_starttag(self, tag, attrs):
        if tag == "header":
            self.headers_started += 1
        if tag == "button":
            self.button_names.append(dict(attrs).get("aria-label"))

    def handle_endtag(self, tag):
        if tag == "header":
            self.headers_ended += 1


class FrozenQualityOracleTests(unittest.TestCase):
    def test_fixture_names_and_labels_are_not_changed(self):
        self.assertEqual(
            [(case["name"], case["kind"]) for case in quality.CASES],
            [
                ("stale_prestart_defect", "positive"),
                ("unknown_owner_defaults_to_self", "positive"),
                ("correct_prestart_guard", "negative"),
                ("correct_owner_validation", "negative"),
                ("defined_callback_not_missing", "negative"),
                ("complete_labeled_html", "negative"),
            ],
        )

    def test_prestart_bug_has_a_concrete_counterexample(self):
        namespace = {}
        exec(compile(source("stale_prestart_defect"), "<trusted-synthetic-stale>", "exec"), namespace)
        # A measurement at 95 ns predates a session opened at 100 ns.
        self.assertTrue(namespace["should_record"](95, 100))
        self.assertTrue(namespace["should_record"](100, 100))

    def test_correct_prestart_guard_rejects_the_same_counterexample(self):
        namespace = {}
        exec(compile(source("correct_prestart_guard"), "<trusted-synthetic-correct>", "exec"), namespace)
        self.assertFalse(namespace["should_record"](95, 100))
        self.assertTrue(namespace["should_record"](100, 100))

    def run_node_fixture(self, name: str, assertions: str):
        if not shutil.which("node"):
            self.skipTest("Node.js required for fixed JavaScript oracle")
        script = ('const assert=require("node:assert/strict");\n'
                  + source(name) + '\n' + assertions + '\n')
        proc = subprocess.run(
            ["node", "-e", script],
            capture_output=True, text=True, timeout=12,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unknown_owner_is_really_misattributed(self):
        self.run_node_fixture(
            "unknown_owner_defaults_to_self",
            "assert.equal(normalizeOwner({owner:'unknown'}), 'self');"
            "assert.equal(normalizeOwner({owner:'other'}), 'other');",
        )

    def test_correct_owner_validation_rejects_unknown(self):
        self.run_node_fixture(
            "correct_owner_validation",
            "assert.throws(()=>normalizeOwner({owner:'unknown'}), /Invalid owner/);"
            "assert.equal(normalizeOwner({owner:'self'}), 'self');",
        )

    def test_defined_callback_is_actually_resolvable(self):
        self.run_node_fixture(
            "defined_callback_not_missing",
            "assert.equal(gpsStart({watchPosition(cb){return cb(42)}}), 42);",
        )

    def test_labeled_html_fragment_has_real_name_and_closed_header(self):
        parser = HtmlStructure()
        parser.feed(source("complete_labeled_html"))
        self.assertEqual(parser.headers_started, 1)
        self.assertEqual(parser.headers_ended, 1)
        self.assertEqual(parser.button_names, ["Save"])
        # This is a valid HTML fragment, not necessarily a standalone page.
        # Absence of literal <body> is not proof of a broken accessible button.


if __name__ == "__main__":
    unittest.main()
