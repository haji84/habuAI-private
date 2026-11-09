"""Real loopback HTTP roundtrip, with synthetic sources and a temporary store."""
import base64
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from wsgiref.simple_server import make_server,WSGIRequestHandler
import test_private_dashboard_sync as fixtures
from test_private_dashboard_sync import LOG,GPX,upload
from scripts.private_dashboard_api import Application
from scripts.private_dashboard_chat import Client,make_batch,repeat_result

class Quiet(WSGIRequestHandler):
    def log_message(self,*args):pass

class HTTPTests(unittest.TestCase):
    def setUp(self):
        fixtures.StoreTests.setUp(self)
        self.token='synthetic-http-only-'+('x'*48)
        self.server=make_server('127.0.0.1',0,lambda e,s:[],handler_class=Quiet)
        self.origin=f'http://127.0.0.1:{self.server.server_port}'
        root=Path(__file__).resolve().parents[1]
        self.server.set_app(Application(self.store,root/'dashboard',self.token,self.origin,allow_http_loopback=True))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        self.client=Client(self.origin,self.token,allow_http_loopback=True)
    def stop(self):
        self.server.shutdown();self.thread.join();self.server.server_close()
    def test_real_http_chat_prepare_apply_reopen_repeat(self):
        p=self.client.call('prepare',{'files':self.files,'channel':'chat'})
        a=self.client.call('apply',{'receipt_id':p['receipt_id'],'batch':make_batch(p,{'2026-11-01':1}),'expected_revision':p['revision']})
        self.assertEqual(self.client.call('status')['revision'],a['revision'])
        repeated=self.client.call('prepare',{'files':self.files,'channel':'dashboard'})
        self.assertEqual(repeat_result(repeated,{'2026-11-01':1})['revision'],1)
        q=self.client.call('prepare',{'files':[upload('log',LOG.replace('11/01','11/02').encode())],'channel':'chat'})
        self.client.call('apply',{'receipt_id':q['receipt_id'],'batch':make_batch(q,{'2026-11-02':0}),'expected_revision':q['revision']})
        self.assertEqual(self.client.call('status')['revision'],2)
        summary=self.store.snapshot()['summary']
        self.assertEqual((summary['total'],summary['effort']['total_nights'],summary['effort']['zero_nights']),(2,3,1))
    def test_anonymous_and_invalid_token_get_no_data(self):
        with self.assertRaises(HTTPError) as error:urlopen(self.origin+'/data/capture_summary.json')
        self.assertEqual(error.exception.code,401);error.exception.close()
        with self.assertRaisesRegex(ValueError,'AUTHENTICATION_REQUIRED'):
            Client(self.origin,'wrong-'+('y'*40),allow_http_loopback=True).call('status')
