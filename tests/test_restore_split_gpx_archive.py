import base64, hashlib, json, lzma, tempfile, unittest
from pathlib import Path
from scripts.restore_split_gpx_archive import restore

class RestoreSplitGpxArchiveTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); parts=root/"parts"; parts.mkdir()
            raw=b"<?xml version='1.0'?><gpx><trk><trkseg><trkpt lat='1' lon='2'/></trkseg></trk></gpx>"
            xz=lzma.compress(raw)
            enc=base64.b64encode(xz).decode("ascii")
            for i in range(0,len(enc),17):
                (parts/f"part_{i//17:03d}.b64").write_text(enc[i:i+17],encoding="ascii")
            manifest={
                "raw_size_bytes":len(raw),
                "raw_sha256":hashlib.sha256(raw).hexdigest(),
                "xz_size_bytes":len(xz),
                "xz_sha256":hashlib.sha256(xz).hexdigest(),
            }
            mp=root/"manifest.json"; mp.write_text(json.dumps(manifest),encoding="utf-8")
            out=root/"out.gpx"
            result=restore(parts,mp,out)
            self.assertEqual(out.read_bytes(),raw)
            self.assertTrue(result["byte_exact"])
if __name__=="__main__":
    unittest.main()
