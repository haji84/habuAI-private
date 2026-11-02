"""RED-first adversarial citation tests; synthetic code only.

A location quote copied solely from a trailing or carried-over comment
must not be accepted as executable evidence even when its line has code.
The original frozen 40 cases and their labels are deliberately untouched.
"""
import unittest

from grounding import added_source_lines, ground_candidates


def ground(source, line, quote):
    lines = source.splitlines()
    patch = "@@ -0,0 +1,{} @@\n".format(len(lines)) + "".join(
        "+" + value + "\n" for value in lines
    )
    row = {"line": line, "code_quote": quote,
           "problem": "A synthetic review allegation anchored on a comment",
           "impact": "Comment prose does not establish a runtime defect"}
    return ground_candidates([row], source, added_source_lines(patch))


class ExecutableCitationBoundaryTests(unittest.TestCase):
    def test_js_trailing_comment_is_not_executable_even_if_line_begins_with_code(self):
        source = "const ok = true; // Missing validation before save\n"
        accepted, reasons = ground(source, 1, "Missing validation before save")
        self.assertEqual(accepted, [])
        self.assertEqual(reasons, {"NON_EXECUTABLE_COMMENT_ANCHOR": 1})

    def test_python_trailing_comment_is_not_executable_evidence(self):
        source = "return True  # Missing database transaction guard\n"
        accepted, reasons = ground(source, 1, "Missing database transaction guard")
        self.assertEqual(accepted, [])
        self.assertEqual(reasons, {"NON_EXECUTABLE_COMMENT_ANCHOR": 1})

    def test_interior_block_comment_after_executable_start_is_not_code(self):
        source = ("const saved = true; /* explanation starts\n"
                  " * Missing persistent storage validation\n"
                  " */\n")
        accepted, reasons = ground(source, 2, "Missing persistent storage validation")
        self.assertEqual(accepted, [])
        self.assertEqual(reasons, {"NON_EXECUTABLE_COMMENT_ANCHOR": 1})

    def test_real_code_adjacent_to_trailing_comment_remains_eligible(self):
        source = "const ok = true; // Missing validation before save\n"
        accepted, reasons = ground(source, 1, "const ok = true;")
        self.assertEqual(len(accepted), 1)
        self.assertEqual(reasons, {"LOCATION_ANCHORED_NOT_BUG_VERIFIED": 1})

    def test_double_slash_in_quoted_string_is_not_a_comment_marker(self):
        source = 'const url = "https://synthetic.invalid";\n'
        accepted, reasons = ground(source, 1, 'url = "https://synthetic.invalid"')
        self.assertEqual(len(accepted), 1)
        self.assertEqual(reasons, {"LOCATION_ANCHORED_NOT_BUG_VERIFIED": 1})

    def test_code_after_closed_inline_block_comment_is_eligible(self):
        source = "/* comment */ const enabled = true;\n"
        accepted, reasons = ground(source, 1, "const enabled = true;")
        self.assertEqual(len(accepted), 1)
        self.assertEqual(reasons, {"LOCATION_ANCHORED_NOT_BUG_VERIFIED": 1})


if __name__ == "__main__":
    unittest.main()
