import io
import unittest
import zipfile

from scripts.audit_legacy_bundle_inventory import audit, classify

class BundleInventoryTests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(classify("x.GPX"),"gpx")
        self.assertEqual(classify("logs/x.txt"),"text")
        self.assertEqual(classify("x.csv"),"csv")

if __name__=="__main__":
    unittest.main()
