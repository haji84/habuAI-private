"""Synthetic private-sync acceptance tests; no owner sources or coordinates."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PrivateDashboardMissingIntegration(unittest.TestCase):
    def test_shared_private_intake_exists(self):
        self.assertTrue((ROOT / 'scripts/private_dashboard_store.py').is_file(),
                        'Shared Chat/dashboard private intake is not implemented')

if __name__ == '__main__':
    unittest.main()
