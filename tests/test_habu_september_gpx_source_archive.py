"""Restore the received September GPX source set; never add capture labels."""
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'incoming/2026-10-21/september_gpx_source_evidence.zip'
RECEIPT = ROOT / 'evidence/raw_intake/2026-10-21-september-gpx-source-evidence.json'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def restore_verified(archive, receipt, destination):
    """Test utility: validate the whole immutable source set before restoring."""
    raw = archive.read_bytes()
    if len(raw) != receipt['archive']['size_bytes'] or digest(raw) != receipt['archive']['sha256']:
        raise ValueError('archive byte identity mismatch')
    expected = {r['member_name']:r for r in receipt['sources']}
    payloads = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        if len(names) != len(expected) or set(names) != set(expected):
            raise ValueError('missing, duplicate, or unexpected source member')
        if z.testzip() is not None:
            raise ValueError('source member CRC mismatch')
        for name, item in expected.items():
            parts = PurePosixPath(name).parts
            if not parts or parts[0] != 'gpx' or '..' in parts or PurePosixPath(name).is_absolute():
                raise ValueError('unsafe source member name')
            payload = z.read(name)
            if len(payload) != item['size_bytes'] or digest(payload) != item['sha256']:
                raise ValueError('source member SHA or byte length mismatch')
            blob = b'blob ' + str(len(payload)).encode() + b'\0' + payload
            if hashlib.sha1(blob).hexdigest() != item['git_blob_sha1']:
                raise ValueError('source member Git blob identity mismatch')
            payloads[name] = payload
    for name, payload in payloads.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(payload)
    return payloads

class SeptemberGpxSourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(ARCHIVE.is_file(), 'September GPX source archive is not staged')
        self.assertTrue(RECEIPT.is_file(), 'September GPX source receipt is not staged')
        self.receipt = json.loads(RECEIPT.read_text(encoding='utf-8'))

    def test_restore_all_fifteen_sources_byte_exactly(self):
        self.assertEqual(self.receipt['member_count'], 15)
        self.assertEqual(self.receipt['quality_status'], 'BYTE_SOURCE_IDENTITY_VERIFIED_ONLY')
        self.assertEqual(self.receipt['added_observation_count'], 0)
        self.assertFalse(self.receipt['complete_search_coverage_claimed'])
        self.assertFalse(self.receipt['negative_eligibility_assigned'])
        self.assertFalse(self.receipt['gold_status_assigned'])
        self.assertEqual(len({r['sha256'] for r in self.receipt['sources']}), 15)
        duplicates = [r for r in self.receipt['sources']
                      if r['duplicate_status'] == 'EXACT_RAW_SHA256_DUPLICATE_OF_MAIN']
        self.assertEqual({r['log_attributed_operational_night'] for r in duplicates},
                         {'2026-09-02', '2026-09-28'})
        with tempfile.TemporaryDirectory() as directory:
            restored = restore_verified(ARCHIVE, self.receipt, Path(directory))
            self.assertEqual(len(restored), 15)
            for item in self.receipt['sources']:
                raw = (Path(directory) / item['member_name']).read_bytes()
                self.assertEqual(digest(raw), item['sha256'])

    def mutated_archive(self, target, *, missing=False):
        with zipfile.ZipFile(ARCHIVE) as source, zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as dest:
            first = source.namelist()[0]
            for name in source.namelist():
                if missing and name == first:
                    continue
                raw = source.read(name)
                if not missing and name == first:
                    raw = bytes([raw[0] ^ 1]) + raw[1:]
                dest.writestr(name, raw)
        # Refresh only the transport digest to exercise the independent member guards.
        receipt = copy.deepcopy(self.receipt)
        receipt['archive']['size_bytes'] = target.stat().st_size
        receipt['archive']['sha256'] = digest(target.read_bytes())
        return receipt

    def test_corrupted_source_member_is_rejected_before_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'corrupted.zip'
            receipt = self.mutated_archive(target)
            restored = Path(directory) / 'restored'
            with self.assertRaisesRegex(ValueError, 'source member SHA'):
                restore_verified(target, receipt, restored)
            self.assertFalse(restored.exists())

    def test_missing_source_member_is_rejected_before_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'missing.zip'
            receipt = self.mutated_archive(target, missing=True)
            restored = Path(directory) / 'restored'
            with self.assertRaisesRegex(ValueError, 'missing, duplicate, or unexpected'):
                restore_verified(target, receipt, restored)
            self.assertFalse(restored.exists())

if __name__ == '__main__':
    unittest.main()
