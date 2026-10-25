import unittest
from scripts.verify_pages_access import AccessGateError, assert_url, check_redirect


class AccessGateTests(unittest.TestCase):
    def test_correct_hosts(self):
        self.assertEqual(assert_url("https://hub-natural-private.pages.dev", preview=False),
                         "https://hub-natural-private.pages.dev/")
        self.assertTrue(assert_url("https://1234.hub-natural-private.pages.dev", preview=True))

    def test_refuse_public_or_misrouted_hosts(self):
        for url, preview in (
            ("http://hub-natural-private.pages.dev", False),
            ("https://example.pages.dev", False),
            ("https://hub-natural-private.pages.dev", True),
            ("https://evil.net/ok", True),
            ("https://hub-natural-private.pages.dev.evil.net", False),
        ):
            with self.subTest(url=url), self.assertRaises(AccessGateError):
                assert_url(url, preview=preview)

    def test_protected_redirect(self):
        check_redirect(code=302, location="https://team.cloudflareaccess.com/cdn-cgi/access/login/xyz")

    def test_public_200_rejected(self):
        with self.assertRaises(AccessGateError):
            check_redirect(code=200, location=None)

    def test_other_redirect_rejected(self):
        with self.assertRaises(AccessGateError):
            check_redirect(code=302, location="https://badsite.example/login")

    def test_403_not_proof(self):
        with self.assertRaises(AccessGateError):
            check_redirect(code=403, location=None)


if __name__ == "__main__":
    unittest.main()
