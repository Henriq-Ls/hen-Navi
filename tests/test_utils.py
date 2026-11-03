import unittest
from urllib.parse import parse_qs, urlsplit

from utils import is_http_url, resolve_address


class ResolveAddressTests(unittest.TestCase):
    def test_domain_defaults_to_https(self):
        self.assertEqual(resolve_address("example.com/path"), "https://example.com/path")

    def test_localhost_and_ip_default_to_http(self):
        self.assertEqual(resolve_address("localhost:8080/app"), "http://localhost:8080/app")
        self.assertEqual(resolve_address("127.0.0.1:5000"), "http://127.0.0.1:5000")
        self.assertEqual(resolve_address("[::1]:9000"), "http://[::1]:9000")

    def test_http_urls_are_preserved(self):
        self.assertEqual(resolve_address("https://example.com/a?q=1"), "https://example.com/a?q=1")
        self.assertTrue(is_http_url("http://localhost:8000"))
        self.assertFalse(is_http_url("file:///etc/passwd"))
        self.assertFalse(is_http_url("https://user:secret@example.com/"))

    def test_search_terms_are_encoded(self):
        target = resolve_address("gatos e cães")
        self.assertEqual(urlsplit(target).netloc, "duckduckgo.com")
        self.assertEqual(parse_qs(urlsplit(target).query)["q"], ["gatos e cães"])

    def test_unsafe_and_unknown_schemes_become_searches(self):
        for value in ("javascript:alert(1)", "file:///etc/passwd", "ftp://example.com"):
            with self.subTest(value=value):
                target = resolve_address(value)
                self.assertEqual(urlsplit(target).scheme, "https")
                self.assertEqual(urlsplit(target).netloc, "duckduckgo.com")

    def test_invalid_domain_and_port_become_searches(self):
        self.assertIn("duckduckgo.com", resolve_address("example-.com").lower())
        self.assertIn("duckduckgo.com", resolve_address("example.com:99999").lower())


if __name__ == "__main__":
    unittest.main()
