"""Fixed two-record positive source crosswalk; no permanent animal identity.

All file reads, time checks and point charges are supplied by the existing Audit.
The returned proof is source consistency, never permission to train or issue P0.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
from pathlib import PureWindowsPath
import re
import xml.etree.ElementTree as ET

from gpx_audit import mark_point_anomalies, match_capture_to_points
from master_contracts import digest
from sept28_positive_source_review import strict_json

PROFILE = 'aug31-owner-capture-occurrence-crosswalk-v1'
NIGHT = '2026-08-31'
JST = timezone(timedelta(hours=9))
REVIEW_NOT_BEFORE = '2026-10-25T15:42:47+00:00'
CAPTURE_PATH = 'data/processed/capture_events/2026/2026-08-31.csv'
INDIVIDUAL_PATH = 'data/processed/individuals/2026/2026-08-31.csv'
REVIEW_PATH = 'evidence/source_reviews/2026-08-31-positive-source-review.json'
CAPTURE_SIZE = 413
CAPTURE_SHA = '137c04b5abe6713c1668633fe10afa61f601a5c0a8d5331471d71f8cbf0a972f'
COORDINATE_METHOD = 'original owner TXT coordinates; real GPX point corroboration; no interpolation'
RECOVERY_CLASS = 'PRESERVED_OWNER_CAPTURE_SOURCE_REVIEW'
SCOPE = 'EXISTING_TWO_SOURCE_CAPTURE_OCCURRENCES_ONLY'
FORBIDDEN_AUTHORITY = (
    'negative_eligibility_assigned', 'search_scope_certified',
    'complete_outcome_coverage_claimed', 'training_authorized',
    'confirmation_authorized', 'official_issuance_authorized',
    'promotion_authorized', 'production_authorized',
)
FIXED = {
    'native_log': ('evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt',
                   116496, '130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c'),
    'native_byte_proof': ('evidence/recovered_sources/2026-08-native-original-library-byte-proof.json',
                          1408, 'a62dd9d612766f6626e2561a0705dbb14cfd1d862e4afc84efec40da34494745'),
    'gpx': ('data/raw/gpx/2026-08-31__legacy.gpx', 4753470,
            '870047567bb0d9bafca0789f768fda3b7b90eb5788f259d043cdb885ce219bd1'),
    'owner_count_record': ('data/reconstructions/habu_captures/2026-08-count-correction-owner-confirmed-47.json',
                           2551, '4fe0fcd7c7e4f67f51d86fc6962d5c2b5ae78d9c04b86412356937f773158c92'),
    'captures': (CAPTURE_PATH, CAPTURE_SIZE, CAPTURE_SHA),
    'individuals': (INDIVIDUAL_PATH, 378,
                    '6d0c01d185722044bf976f2858461990518dffe6ee402815269ad94f5f242947'),
}
# These keys are newly derived record/occurrence references, NOT original animal IDs.
EXPECTED = (
    ('AUG31SRC-L10110', 10110, 10119, 112368, 112489,
     '0e3ef4d50ff5cf9c98b3e0012d9fc75e7a24d6667e0f6b5f259ed5a86e7b4581',
     '2026-08-31T21:43:00+09:00', '', (10117, 10118)),
    ('AUG31SRC-L10492', 10492, 10500, 116249, 116392,
     '6bd4b0ed2c572d9b0bd39f8137456e53c7721028f7f88e6e03e4a822c88bceea',
     '2026-09-01T01:17:00+09:00', '瀬戸内町県道626号', (10499, 10500)),
)
REVIEW_FIELDS = set(FORBIDDEN_AUTHORITY) | {
    'schema_version', 'verification_profile', 'source_sha256', 'use_roles',
    'reviewed_at', 'cohort_exposure', 'scope', 'independent_device_authentication',
    'permanent_biological_identity', 'coordinate_method', 'recovery_class',
    'source_refs', 'proof', 'proof_sha256',
}



from _owner_capture_occurrence_core import Definition, Record
import _owner_capture_occurrence_core as _core

_DEFINITION = Definition(tuple((key, *value) for key, value in FIXED.items()),
    tuple(Record(*row, note="ハブ捕獲100~120オス", size_note="100~120", sex="オス") for row in EXPECTED),
    NIGHT, 17906)

def is_capture_path(value):
    """Recognize aliases of this sole new CSV, so they cannot use legacy admission."""
    return type(value) is str and PureWindowsPath(value).as_posix().casefold() == CAPTURE_PATH.casefold()


_time = _core._time
_hash = _core._hash
_digest = _core._digest
_owned_review = _core._owned_review
_csv = _core._csv
_coordinate = _core._coordinate

def _points(raw, tick, consume_point):
    return _core._points(raw, tick, consume_point, definition=_DEFINITION)

def _cross_bind(payloads, *, tick, consume_point):
    return _core._cross_bind(payloads, definition=_DEFINITION, tick=tick, consume_point=consume_point)

def reproduce_sources(refs, *, read_ref, tick, consume_point):
    return _core.reproduce_sources(refs, definition=_DEFINITION, read_ref=read_ref,
                                   tick=tick, consume_point=consume_point)

def verify_review(review, *, read_ref, tick, consume_point, now):
    review = _owned_review(review, tick)
    if (set(review) != REVIEW_FIELDS or review.get('schema_version') != '1.0'
            or review.get('verification_profile') != PROFILE or review.get('source_sha256') != CAPTURE_SHA
            or review.get('use_roles') not in (['diagnostic_only'], ['outcome_label'])
            or review.get('scope') != SCOPE or review.get('cohort_exposure') != 'RESEARCH_EXPOSED'
            or review.get('independent_device_authentication') != 'NOT_ESTABLISHED'
            or review.get('permanent_biological_identity') != 'NOT_ESTABLISHED'
            or review.get('coordinate_method') != COORDINATE_METHOD or review.get('recovery_class') != RECOVERY_CLASS
            or any(review.get(key) is not False for key in FORBIDDEN_AUTHORITY)
            or not _time(REVIEW_NOT_BEFORE) <= _time(review['reviewed_at']) <= _time(now)):
        raise ValueError('AUG31_PROFILE_OR_AUTHORITY')
    proof = reproduce_sources(review['source_refs'], read_ref=read_ref, tick=tick, consume_point=consume_point)
    if (_digest(review['proof'], tick) != _digest(proof, tick)
            or review['proof_sha256'] != _digest(proof, tick)):
        raise ValueError('AUG31_PROOF_BINDING')
    tick();return proof
