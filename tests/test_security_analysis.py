import unittest

from _SERVICOS_.security_analysis import (
    analyze_url_safety,
    inspect_security_headers,
)


class SecurityAnalysisTests(unittest.TestCase):
    def test_http_and_punycode_addresses_show_local_warnings(self):
        result = analyze_url_safety("http://xn--pple-43d.example/login")

        self.assertEqual(result["host"], "xn--pple-43d.example")
        self.assertTrue(any("HTTP sem criptografia" in item for item in result["findings"]))
        self.assertTrue(any("punycode" in item for item in result["findings"]))

    def test_https_with_userinfo_is_flagged(self):
        result = analyze_url_safety("https://user:secret@example.com/")

        self.assertTrue(any("usuário ou senha" in item for item in result["findings"]))

    def test_normal_https_address_does_not_claim_site_is_safe(self):
        result = analyze_url_safety("https://example.com/")

        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("não garante", result["findings"][0])

    def test_security_headers_are_reported_without_inference(self):
        report = inspect_security_headers(
            [
                (b"Content-Security-Policy", b"default-src 'self'; frame-ancestors 'none'"),
                (b"X-Content-Type-Options", b"nosniff"),
            ]
        )
        by_name = {item["name"]: item["present"] for item in report}

        self.assertTrue(by_name["Content-Security-Policy"])
        self.assertTrue(by_name["X-Content-Type-Options"])
        self.assertTrue(by_name["Proteção contra incorporação em frames"])
        self.assertFalse(by_name["HSTS"])


if __name__ == "__main__":
    unittest.main()
