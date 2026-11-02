"""Offline red/green checks for exact-line review evidence (no model calls)."""
import unittest

from grounding import added_source_lines, ground_candidates

PATCH = (
    'diff --git a/dashboard/x.js b/dashboard/x.js\n'
    '--- a/dashboard/x.js\n'
    '+++ b/dashboard/x.js\n'
    '@@ -1,3 +1,4 @@\n'
    ' const before=1;\n'
    '-old();\n'
    '+function ownerOf(item) {\n'
    "+ return item.owner==='other'?'other':'self';\n"
    '+}\n'
    ' const after=2;\n'
)
SOURCE = (
    'const before=1;\n'
    'function ownerOf(item) {\n'
    " return item.owner==='other'?'other':'self';\n"
    '}\n'
    'const after=2;\n'
)


class GroundingContractTests(unittest.TestCase):
    def test_added_line_numbers(self):
        lines = added_source_lines(PATCH)
        self.assertEqual(lines, {
            2: 'function ownerOf(item) {',
            3: " return item.owner==='other'?'other':'self';",
            4: '}',
        })

    def test_correct_quote_on_actual_added_line(self):
        row = {'line': 3, 'code_quote': "item.owner==='other'?'other':'self'",
               'problem': 'Unknown owner values become a self capture'}
        actual, counts = ground_candidates([row], SOURCE, added_source_lines(PATCH))
        self.assertEqual(len(actual), 1)
        self.assertEqual(counts['LOCATION_ANCHORED_NOT_BUG_VERIFIED'], 1)

    def test_hallucinated_line_and_unchanged_context_rejected(self):
        rows = [
            {'line': 12, 'code_quote': 'some purported line'},
            {'line': 1, 'code_quote': 'const before=1;'},
        ]
        actual, counts = ground_candidates(rows, SOURCE, added_source_lines(PATCH))
        self.assertEqual(actual, [])
        self.assertEqual(counts['NONEXISTENT_SOURCE_LINE'], 1)
        self.assertEqual(counts['NOT_AN_ADDED_SOURCE_LINE'], 1)

    def test_fabricated_quote_missing_quote_and_vague_quote_rejected(self):
        rows = [
            {'line': 3, 'code_quote': 'getTrustedOwner(item)'},
            {'line': 3, 'code_quote': ''},
            {'line': 3, 'code_quote': 'item'},
        ]
        actual, counts = ground_candidates(rows, SOURCE, added_source_lines(PATCH))
        self.assertEqual(actual, [])
        self.assertEqual(sum(counts.values()), len(rows))

    def test_comment_only_quote_cannot_prove_runtime_defect(self):
        for comment in (
            '# Requirement: must not export private GPS',
            '// Requirement: FREE plan must not export',
            '/* Documentation: never leak locations */',
            '<!-- A button must have an accessible name -->',
        ):
            with self.subTest(comment=comment):
                patch = '@@ -0,0 +1 @@\\n+' + comment + '\\n'
                # Keep newlines real, not literal backslash-n.
                patch = patch.replace('\\n', '\n')
                actual, counts = ground_candidates(
                    [{'line': 1, 'code_quote': comment}],
                    comment + '\n',
                    added_source_lines(patch),
                )
                self.assertEqual(actual, [])
                self.assertEqual(counts, {'NON_EXECUTABLE_COMMENT_ANCHOR': 1})

    def test_multiline_comment_interiors_do_not_anchor_defect_claims(self):
        for source in (
            ('/*\n * Requirement: FREE must not export\n */\n'
             "function canExport(plan) { return plan !== 'FREE'; }\n"),
            ('<!--\nRequirement: button must have a label\n-->\n'
             '<button aria-label="Save">Save</button>\n'),
        ):
            with self.subTest(source=source):
                patch = '@@ -0,0 +1,4 @@\n' + ''.join(
                    '+' + line + '\n' for line in source.splitlines()
                )
                lines = source.splitlines()
                rows = [
                    {'line': 2, 'code_quote': lines[1],
                     'problem': 'Requirement text is not executable'},
                    {'line': 4, 'code_quote': lines[3],
                     'problem': 'Citing actual executable or HTML source'},
                ]
                accepted, counts = ground_candidates(
                    rows, source, added_source_lines(patch)
                )
                self.assertEqual([x['line'] for x in accepted], [4])
                self.assertEqual(counts['NON_EXECUTABLE_COMMENT_ANCHOR'], 1)
                self.assertEqual(counts['LOCATION_ANCHORED_NOT_BUG_VERIFIED'], 1)

    def test_code_following_closed_block_comment_stays_eligible(self):
        source = ('/* Commentary only\n'
                  ' */ const allowed = false;\n')
        patch = '@@ -0,0 +1,2 @@\n' + ''.join(
            '+' + line + '\n' for line in source.splitlines()
        )
        row = {'line': 2, 'code_quote': 'const allowed = false;',
               'problem': 'A finding about the executable statement'}
        accepted, counts = ground_candidates(
            [row], source, added_source_lines(patch)
        )
        self.assertEqual(len(accepted), 1)
        self.assertEqual(counts['LOCATION_ANCHORED_NOT_BUG_VERIFIED'], 1)

    def test_executable_line_next_to_comment_remains_groundable(self):
        source = ('// Requirement: reject FREE export\n'
                  "function canExport(plan) { return plan !== 'FREE'; }\n")
        patch = ('@@ -0,0 +1,2 @@\n'
                 '+// Requirement: reject FREE export\n'
                 "+function canExport(plan) { return plan !== 'FREE'; }\n")
        rows = [
            {'line': 1, 'code_quote': '// Requirement: reject FREE export'},
            {'line': 2, 'code_quote': "return plan !== 'FREE'"},
        ]
        accepted, reasons = ground_candidates(rows, source, added_source_lines(patch))
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]['line'], 2)
        self.assertEqual(reasons['NON_EXECUTABLE_COMMENT_ANCHOR'], 1)
        self.assertEqual(reasons['LOCATION_ANCHORED_NOT_BUG_VERIFIED'], 1)

    def test_duplicate_suggestion_counted_not_silently_discarded(self):
        row = {'line': 3, 'code_quote': "item.owner==='other'?'other':'self'",
               'problem': 'Unknown owner defaults to self'}
        actual, counts = ground_candidates([row, row], SOURCE, added_source_lines(PATCH))
        self.assertEqual(len(actual), 1)
        self.assertEqual(counts['EXACT_DUPLICATE_CANDIDATE'], 1)

    def test_long_one_line_script_supports_exact_substring(self):
        patch = '@@ -0,0 +1 @@\n+const a=1,b=2;function total(){return a+b;}\n'
        actual, counts = ground_candidates(
            [{'line': 1, 'code_quote': 'function total(){return a+b;}'}],
            'const a=1,b=2;function total(){return a+b;}\n',
            added_source_lines(patch),
        )
        self.assertEqual(len(actual), 1)

    def test_malformed_or_empty_diff_fails_closed(self):
        with self.assertRaises(ValueError):
            added_source_lines('@@ -0,0 +1 @@\n+valid\nGARBAGE\n')
        with self.assertRaises(ValueError):
            added_source_lines('diff --git a/x b/x\n')

    def test_quote_must_match_both_patch_and_head_source(self):
        actual, counts = ground_candidates(
            [{'line': 3, 'code_quote': "item.owner==='other'?'other':'self'"}],
            SOURCE.replace('self', 'unknown'),
            added_source_lines(PATCH),
        )
        self.assertEqual(actual, [])
        self.assertEqual(counts['NOT_AN_ADDED_SOURCE_LINE'], 1)


if __name__ == '__main__':
    unittest.main()
