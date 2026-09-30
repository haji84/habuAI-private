import hashlib
import io
import unittest
import zipfile

from scripts.migrate_legacy_baseline_log import extract, EXPECTED_SHA256

class LegacyBaselineLogTests(unittest.TestCase):
    def test_expected_sha_is_fixed(self):
        self.assertEqual(len(EXPECTED_SHA256),64)

if __name__=="__main__":
    unittest.main()
