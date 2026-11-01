"""Conservative source-line verification for advisory code-review suggestions.

A grounded location is NOT evidence that the model's alleged bug is real.
Only actual added lines in a complete, immutable file diff can be cited.
No model inference, network, or raw user records are accessed here.
"""
from __future__ import annotations

import re

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


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
        elif not isinstance(quote, str) or not quote.strip():
            reason = 'MISSING_VERBATIM_QUOTE'
        elif '\n' in quote or '\r' in quote or len(quote) > 180:
            reason = 'INVALID_QUOTE'
        elif len(quote.strip()) < 12 and quote.strip() != text[line - 1].strip():
            reason = 'QUOTE_TOO_SHORT'
        elif quote not in text[line - 1]:
            reason = 'QUOTED_TEXT_NOT_ON_SOURCE_LINE'
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
