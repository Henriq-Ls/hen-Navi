import unittest
import tempfile
from pathlib import Path

from _SERVICOS_.adblock_rules import BlocklistFile, BlocklistMatcher, parse_blocklist
from _ULTILIDADES_.site_utils import (
    domain_matches,
    extract_site_host,
    is_valid_https_url,
    normalize_host,
)


class SiteUtilsTests(unittest.TestCase):
    def test_extracts_host_and_removes_only_leading_www(self):
        self.assertEqual(
            extract_site_host("https://www.loja.example.com:8443/produto"),
            "loja.example.com",
        )
        self.assertEqual(extract_site_host("file:///tmp/inicio.html"), "")
        self.assertEqual(extract_site_host("https://[::1]:8443/"), "::1")

    def test_normalizes_idn_and_rejects_malformed_hosts(self):
        self.assertEqual(
            normalize_host("WWW.ação.example", strip_www=True),
            "xn--ao-siap.example",
        )
        self.assertEqual(normalize_host("bad host.example"), "")

    def test_domain_match_respects_label_boundaries(self):
        self.assertTrue(domain_matches("cdn.ads.example.com", "ads.example.com"))
        self.assertTrue(domain_matches("ads.example.com", "ads.example.com"))
        self.assertFalse(domain_matches("notads.example.com", "ads.example.com"))

    def test_https_list_url_validation(self):
        self.assertTrue(is_valid_https_url("https://lists.example.org/hosts.txt"))
        self.assertFalse(is_valid_https_url("http://lists.example.org/hosts.txt"))
        self.assertFalse(is_valid_https_url("https://user:pass@lists.example.org/list"))


class BlocklistTests(unittest.TestCase):
    def test_parses_hosts_and_simple_adblock_rules_only(self):
        domains = parse_blocklist(
            """
            # comment
            0.0.0.0 ads.example.com tracker.example.net
            ||pixel.example.org^
            ||unsupported.example.org^$script
            ||wild.example.org/path^
            127.0.0.1 localhost
            """
        )
        self.assertEqual(
            domains,
            frozenset(
                {
                    "ads.example.com",
                    "tracker.example.net",
                    "pixel.example.org",
                }
            ),
        )

    def test_blocks_subdomains_but_not_main_document_or_exception_sites(self):
        matcher = BlocklistMatcher({"ads.example.com"})
        blocked = matcher.should_block(
            "https://img.cdn.ads.example.com/banner.js",
            "https://news.example.net/story",
            is_main_frame=False,
            enabled=True,
        )
        self.assertTrue(blocked)
        self.assertFalse(
            matcher.should_block(
                "https://ads.example.com/",
                "https://news.example.net/story",
                is_main_frame=True,
                enabled=True,
            )
        )
        self.assertFalse(
            matcher.should_block(
                "https://ads.example.com/banner.js",
                "https://sub.shop.example.net/",
                is_main_frame=False,
                enabled=True,
                exceptions={"shop.example.net"},
            )
        )
        self.assertFalse(
            matcher.should_block(
                "https://ads.example.com/banner.js",
                "https://news.example.net/",
                is_main_frame=False,
                enabled=False,
            )
        )

    def test_www_request_matches_a_rule_for_that_exact_subdomain(self):
        matcher = BlocklistMatcher({"www.ads.example.com"})
        self.assertTrue(
            matcher.should_block(
                "https://www.ads.example.com/banner.js",
                "https://news.example.net/",
                is_main_frame=False,
                enabled=True,
            )
        )

    def test_blocklist_file_uses_defaults_and_replaces_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            blocklist_path = Path(directory) / "rules.txt"
            blocklist = BlocklistFile(blocklist_path)

            defaults = blocklist.ensure()
            self.assertTrue(blocklist_path.is_file())
            self.assertIn("doubleclick.net", defaults)

            updated = blocklist.replace("0.0.0.0 ads.example.org\n")
            self.assertEqual(updated, frozenset({"ads.example.org"}))
            self.assertEqual(blocklist.load(), updated)
            with self.assertRaises(ValueError):
                blocklist.replace("||not-a-supported-rule^$script\n")
            self.assertEqual(blocklist.load(), updated)


if __name__ == "__main__":
    unittest.main()
