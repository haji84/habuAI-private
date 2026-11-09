"""Chat transport tests: fixed origin, no redirects, exact source bytes."""
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
class ChatTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'scripts/private_dashboard_chat.py').is_file(),'Chat transport missing')
        self.m=importlib.import_module('scripts.private_dashboard_chat')
    def test_refuses_http_credentials_path_query_and_userinfo(self):
        for origin in ['http://example.test','https://user:pass@example.test','https://example.test/path','https://example.test?token=x']:
            with self.subTest(origin=origin):
                with self.assertRaises(ValueError):self.m.Client(origin,'x'*40)
    def test_source_encoding_preserves_crlf(self):
        import base64
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.txt';p.write_bytes(b'first\r\nsecond\r\n')
            self.assertEqual(base64.b64decode(self.m.source('log',p)['content_b64']),p.read_bytes())
    def test_confirmations_are_explicit_bounded_and_unique(self):
        self.assertEqual(self.m.confirmations(['2026-11-01=0']),{'2026-11-01':0})
        for values in [['2026-11-01=-1'],['2026-11-01=1','2026-11-01=2'],['2026-02-30=1'],['2026-11-01=true']]:
            with self.assertRaises(ValueError):self.m.confirmations(values)
    def test_redirect_handler_never_forwards_secret(self):
        from urllib.request import Request
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError):
            self.m.NoRedirect().redirect_request(Request('https://owner.test'),None,302,'redirect',{},'https://other.test')
    def test_lost_response_repeat_checks_original_confirmations(self):
        p={'state':'APPLIED','receipt_id':'a'*64,'applied_revision':1,'applied_confirmations':{'2026-11-01':1}}
        self.assertEqual(self.m.repeat_result(p,{'2026-11-01':1})['revision'],1)
        with self.assertRaises(ValueError):self.m.repeat_result(p,{'2026-11-01':2})
