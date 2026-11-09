"""Public CI regression tests with synthetic, non-owner, non-location fixtures."""
import base64
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.dashboard_release.prepare_vercel_release import load_three_file_archive, vercel_config, build_release, ReleaseRejected, validate_counts


def make_files():
    summary = {
        'asof':'2026-02-02','capture_total':3,'capture_total_status':'OWNER_CONFIRMED_RECONCILED',
        'effort_nights':2,'models':[{'kind':k,'status':'RESEARCH_ONLY','events':None,'individuals':None,'nights':None}
            for k in ('night_count','capture_clock','spatial_positive','all_owner_nights')],
        'months':[{'month':'2026-01','captures':1,'cumulative':1,'effort_nights':1,'positive_nights':1,'zero_nights':0},
                  {'month':'2026-02','captures':2,'cumulative':3,'effort_nights':1,'positive_nights':1,'zero_nights':0}],
        'non_search_days':1,'official_model_status':'BLOCKED','owner_reported_total':3,
        'publication_scope':'MONTHLY_AGGREGATES_ONLY_NO_INDIVIDUAL_RECORDS',
        'schema_version':'habu-public-aggregate-v1','total_difference':0,'year':2026,
        'owner_confirmation_day_jst':'2026-02-03',
        'owner_confirmation_scope':'ANNUAL_AGGREGATE_ONLY_NOT_INDIVIDUAL_EVIDENCE'
    }
    js = '(()=>{const n=1;})();'
    style='body{color:gold}'
    sh=base64.b64encode(hashlib.sha256(js.encode()).digest()).decode()
    st=base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    csp=("default-src 'none'; script-src 'sha256-"+sh+"'; style-src 'sha256-"+st+
         "'; base-uri 'none'; form-action 'none'; connect-src 'none'; object-src 'none'")
    content=json.dumps(summary,ensure_ascii=False,sort_keys=True)
    html=('<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="'+csp+'"><style>'+style+'</style></head>'
          '<body><script id="public-summary" type="application/json">'+content+'</script><script data-runtime>'+js+'</script></body></html>')
    headers=("/*\n  Content-Security-Policy: "+csp+"; frame-ancestors 'none'\n  X-Content-Type-Options: nosniff\n"
             "  Referrer-Policy: no-referrer\n  Cache-Control: no-cache\n")
    return {'index.html':html.encode(),'_headers':headers.encode(),'data/public_summary.json':(content+'\n').encode()}


class VercelAggregateReleaseTests(unittest.TestCase):
    def setUp(self):
        self.files=make_files()
    def write_archive(self,path,files):
        with zipfile.ZipFile(path,'w') as z:
            for name,b in files.items():z.writestr(name,b)
    def mutate_summary(self,mutate):
        d=json.loads(self.files['data/public_summary.json']);mutate(d)
        return json.dumps(d,ensure_ascii=False).encode()
    def test_synthetic_aggregate(self):
        d=validate_counts(self.files['data/public_summary.json'])
        self.assertEqual(d['capture_total'],3)
    def test_vercel_headers_same_csp_as_html(self):
        c=vercel_config(self.files)
        self.assertIsNone(c['framework'])
        self.assertFalse(c['public'])
        self.assertEqual(len(c['headers']),1)
        self.assertIn("frame-ancestors 'none'",c['headers'][0]['headers'][0]['value'])
    def test_no_private_members_allowed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'input.zip'
            extra=dict(self.files);extra['raw/capture.gpx']=b'synthetic'
            self.write_archive(p,extra)
            with self.assertRaises(ReleaseRejected):load_three_file_archive(p)
    def test_aggregate_rejects_coordinate_key(self):
        with self.assertRaises(ReleaseRejected):validate_counts(self.mutate_summary(lambda d:d.update({'lat':0.0})))
    def test_reject_tampered_annual(self):
        with self.assertRaises(ReleaseRejected):validate_counts(self.mutate_summary(lambda d:d.update({'capture_total':4})))
    def test_reject_tampered_month(self):
        with self.assertRaises(ReleaseRejected):validate_counts(self.mutate_summary(lambda d:d['months'][-1].update({'captures':3})))
    def test_reject_model_champion_claim(self):
        with self.assertRaises(ReleaseRejected):validate_counts(self.mutate_summary(lambda d:d.update({'official_model_status':'APPROVED'})))
    def test_reject_owner_discrepancy_claim(self):
        with self.assertRaises(ReleaseRejected):validate_counts(self.mutate_summary(lambda d:d.update({'owner_reported_total':2})))
    def test_reject_header_relax(self):
        f=dict(self.files);f['_headers']=f['_headers'].replace(b"connect-src 'none'",b"connect-src *")
        with self.assertRaises(ReleaseRejected):vercel_config(f)
    def test_reject_runtime_script_change(self):
        f=dict(self.files);f['index.html']=f['index.html'].replace(b'const n=1',b'const n=2')
        with self.assertRaises(ReleaseRejected):vercel_config(f)
    def test_reject_html_data_mismatch(self):
        f=dict(self.files);f['index.html']=f['index.html'].replace(b'"capture_total": 3',b'"capture_total": 4')
        with self.assertRaises(ReleaseRejected):vercel_config(f)
    def test_reject_duplicate_json_keys(self):
        d=self.files['data/public_summary.json'].replace(b'"year": 2026',b'"year": 2026, "year": 2026')
        with self.assertRaises(ReleaseRejected):validate_counts(d)
    def test_package_exact_three_files_and_idempotence_block(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'input.zip';out=Path(t)/'out'
            self.write_archive(src,self.files)
            result=build_release(src,out)
            self.assertTrue(result['not_deployed'])
            self.assertEqual(set(result['allowed_files']),{'index.html','data/public_summary.json','vercel.json'})
            self.assertEqual(len([x for x in out.rglob('*') if x.is_file()]),3)
            with self.assertRaises(ReleaseRejected):build_release(src,out)

if __name__=='__main__': unittest.main()