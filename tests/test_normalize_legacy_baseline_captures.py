import unittest
from scripts.normalize_legacy_baseline_captures import operational_night, parse_captures
from datetime import datetime, timezone, timedelta

JST=timezone(timedelta(hours=9))

class NormalizeLegacyCaptureTests(unittest.TestCase):
    def test_0700_boundary(self):
        self.assertEqual(operational_night(datetime(2026,8,2,0,50,tzinfo=JST)),"2026-08-01")
        self.assertEqual(operational_night(datetime(2026,8,2,7,0,tzinfo=JST)),"2026-08-02")

    def test_capture_block(self):
        text="""2026/08/02 0:50
捕獲
ハブ捕獲中
移動中 海に向かって
道路脇
ドライ
瀬戸内町阿木名
28.16784377023349
129.3368015044549
"""
        rows=parse_captures(text,"x"*64)
        self.assertEqual(len(rows),1)
        r=rows[0]
        self.assertEqual(r["operational_date"],"2026-08-01")
        self.assertEqual(r["event_count"],1)
        self.assertEqual(r["size_class_legacy"],"中")
        self.assertEqual(r["surface"],"ドライ")
        self.assertAlmostEqual(float(r["latitude"]),28.16784377023349)

if __name__=="__main__":
    unittest.main()
