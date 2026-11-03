"""Conservative source-line verification for advisory code-review suggestions.

A grounded location is NOT evidence that the model's alleged bug is real.
Only actual added lines in a complete, immutable file diff can be cited.
No model inference, network, or raw user records are accessed here.
"""
from __future__ import annotations

import re

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _non_executable_comment_line(lines: list[str], index: int) -> bool:
    """Reject whole-line comments including interior lines of block comments.

    This is a conservative citation filter, not a language parser or proof
    that any remaining source-anchored claim is a real software defect.
    """
    block_end = None
    comment_only = False
    for raw in lines[:index + 1]:
        part = raw.lstrip()
        if block_end is not None:
            closing_at = part.find(block_end)
            if closing_at < 0:
                comment_only = True
            else:
                comment_only = not bool(part[closing_at + len(block_end):].strip())
                block_end = None
        elif part.startswith(('#', '//', '*/', '-->')):
            comment_only = True
        elif part.startswith(('/*', '<!--')):
            end = '*/' if part.startswith('/*') else '-->'
            closing_at = part.find(end, 2 if end == '*/' else 4)
            if closing_at < 0:
                block_end = end
                comment_only = True
            else:
                comment_only = not bool(part[closing_at + len(end):].strip())
        else:
            comment_only = False
    return comment_only


def _source_code_without_comments(lines: list[str], index: int) -> str:
    """Read-only comment masking for a candidate line, including prior blocks.

    Preserve quoted string literals containing // or #, but never allow a
    code_quote supported only by trailing or multiline comment prose.
    This is deliberately conservative, NOT a semantic code verifier.
    """
    block_end = None
    for line_number, raw in enumerate(lines[:index + 1]):
        position = 0
        executable = []
        while position < len(raw):
            if block_end is not None:
                end = raw.find(block_end, position)
                if end < 0:
                    break
                position = end + len(block_end)
                block_end = None
                continue
            if raw.startswith('<!--', position):
                block_end = '-->'
                position += 4
                continue
            if raw.startswith('/*', position):
                block_end = '*/'
                position += 2
                continue
            if raw.startswith('//', position) or raw[position] == '#':
                break
            if raw[position] in ("'", '"', '`'):
                delimiter = raw[position]
                start = position
                position += 1
                while position < len(raw):
                    if raw[position] == chr(92):
                        position = min(len(raw), position + 2)
                    elif raw[position] == delimiter:
                        position += 1
                        break
                    else:
                        position += 1
                executable.append(raw[start:position])
                continue
            executable.append(raw[position])
            position += 1
        if line_number == index:
            return ''.join(executable)
    return ''


def added_source_lines(patch: str) -> dict[int, str]:
    """Map added lines to their real new-file line numbers in full git diff."""
    current = None
    added: dict[int, str] = {}
    for raw in patch.splitlines():
        m = HUNK.match(raw)
        if m is not None:
            current = int(m.group(1))
            continue
        if current is None:
            continue
        if raw.startswith('+++ ') or raw.startswith('--- ') or raw.startswith('diff --git '):
            current = None
            continue
        if raw.startswith('\\ No newline at end of file'):
            continue
        if raw.startswith('+'):
            if current in added:
                raise ValueError('Duplicate new-file line in diff')
            added[current] = raw[1:]
            current += 1
        elif raw.startswith(' '):
            current += 1
        elif raw.startswith('-'):
            continue
        else:
            # A malformed hunk must never create fictitious line anchors.
            raise ValueError('Malformed diff hunk')
    if not added:
        raise ValueError('Expected newly added source line(s)')
    return added


def ground_candidates(rows: list[dict], source: str,
                      added: dict[int, str]) -> tuple[list[dict], dict[str, int]]:
    """Verify exact cited bytes; classify all others without deleting them.

    code_quote must be a verbatim substring on the exact added source line.
    Source-line confirmation means LOCATION_ONLY, never confirmed correctness.
    """
    text = source.splitlines()
    accepted: list[dict] = []
    reasons: dict[str, int] = {}
    seen: set[tuple[int, str, str]] = set()
    for row in rows:
        line = row.get('line')
        quote = row.get('code_quote')
        if not isinstance(line, int) or isinstance(line, bool) or line < 1 or line > len(text):
            reason = 'NONEXISTENT_SOURCE_LINE'
        elif line not in added or text[line - 1] != added[line]:
            reason = 'NOT_AN_ADDED_SOURCE_LINE'
        elif _non_executable_comment_line(text, line - 1):
            # A requirement written in a comment is not executed code.
            # The model may cite it as context, but it cannot by itself
            # demonstrate a behavioral defect in the implementation.
            reason = 'NON_EXECUTABLE_COMMENT_ANCHOR'
        elif not isinstance(quote, str) or not quote.strip():
            reason = 'MISSING_VERBATIM_QUOTE'
        elif '\n' in quote or '\r' in quote or len(quote) > 180:
            reason = 'INVALID_QUOTE'
        elif len(quote.strip()) < 12 and quote.strip() != text[line - 1].strip():
            reason = 'QUOTE_TOO_SHORT'
        elif quote not in text[line - 1]:
            reason = 'QUOTED_TEXT_NOT_ON_SOURCE_LINE'
        elif quote not in _source_code_without_comments(text, line - 1):
            reason = 'NON_EXECUTABLE_COMMENT_ANCHOR'
        else:
            identity = (line, quote, ' '.join(str(row.get('problem', '')).lower().split()))
            if identity in seen:
                reason = 'EXACT_DUPLICATE_CANDIDATE'
            else:
                seen.add(identity)
                accepted.append(dict(row))
                reason = 'LOCATION_ANCHORED_NOT_BUG_VERIFIED'
        reasons[reason] = reasons.get(reason, 0) + 1
    if len(rows) != sum(reasons.values()):
        raise AssertionError('Candidate lost during grounding')
    return accepted, reasons
