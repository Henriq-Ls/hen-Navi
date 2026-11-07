import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _SERVICOS_.web_credential_store as web_credential_store
from _SERVICOS_.secure_keyring import SecureKeyringError
from _SERVICOS_.web_credential_store import (
    WebCredentialStore,
    WebCredentialStoreError,
    origin_for_url,
)


class FakeKeyring:
    secrets = {}

    @classmethod
    def get_password(cls, service, username):
        return cls.secrets.get((service, username))

    @classmethod
    def set_password(cls, service, username, password):
        cls.secrets[(service, username)] = password

    @classmethod
    def delete_password(cls, service, username):
        cls.secrets.pop((service, username), None)


class WebCredentialStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = WebCredentialStore(self.temp.name)
        FakeKeyring.secrets.clear()
        patcher = patch.object(
            web_credential_store,
            "get_secure_keyring",
            return_value=FakeKeyring,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_origin_keeps_exact_https_site_and_discards_path(self):
        self.assertEqual(
            origin_for_url("https://www.replit.com/login?next=/"),
            "https://www.replit.com",
        )
        self.assertEqual(
            origin_for_url("https://replit.com:8443/login"),
            "https://replit.com:8443",
        )

    def test_rejects_http_and_userinfo_urls(self):
        for url in (
            "http://replit.com/login",
            "https://user:secret@replit.com/login",
        ):
            with self.subTest(url=url), self.assertRaises(
                WebCredentialStoreError
            ):
                origin_for_url(url)

    def test_secret_is_only_in_system_keyring(self):
        username = "user@example.com"
        password = "never-write-this-password"
        credential_id = self.store.save_login(
            "https://replit.com/login",
            username,
            password,
        )

        metadata = Path(self.store.path).read_text(encoding="utf-8")
        self.assertNotIn(username, metadata)
        self.assertNotIn(password, metadata)
        self.assertEqual(
            self.store.list_for_origin("https://replit.com"),
            [{"id": credential_id, "username": username}],
        )
        self.assertEqual(
            self.store.get_login(credential_id, "https://replit.com/login"),
            {"username": username, "password": password},
        )

    def test_same_site_username_updates_existing_keyring_entry(self):
        first_id = self.store.save_login(
            "https://replit.com",
            "user@example.com",
            "old-password",
        )
        second_id = self.store.save_login(
            "https://replit.com/settings",
            "user@example.com",
            "new-password",
        )

        self.assertEqual(first_id, second_id)
        metadata = json.loads(Path(self.store.path).read_text(encoding="utf-8"))
        self.assertEqual(len(metadata["credentials"]), 1)
        self.assertEqual(
            self.store.get_login(second_id, "https://replit.com")["password"],
            "new-password",
        )

    def test_login_cannot_be_retrieved_for_another_origin(self):
        credential_id = self.store.save_login(
            "https://replit.com",
            "user@example.com",
            "secret",
        )
        with self.assertRaises(WebCredentialStoreError):
            self.store.get_login(credential_id, "https://evil.example")
        self.assertEqual(
            self.store.list_for_origin("https://www.replit.com"),
            [],
        )

    def test_delete_removes_metadata_and_keyring_secret(self):
        credential_id = self.store.save_login(
            "https://replit.com",
            "user@example.com",
            "secret",
        )
        self.store.delete_login(credential_id, "https://replit.com")

        self.assertEqual(self.store.list_for_origin("https://replit.com"), [])
        self.assertNotIn(
            (web_credential_store.SERVICE_KEYRING, credential_id),
            FakeKeyring.secrets,
        )

    def test_unavailable_keyring_fails_without_file_fallback(self):
        with patch.object(
            web_credential_store,
            "get_secure_keyring",
            side_effect=SecureKeyringError("cofre indisponível"),
        ):
            with self.assertRaises(WebCredentialStoreError):
                self.store.save_login(
                    "https://replit.com",
                    "user@example.com",
                    "secret",
                )
        self.assertFalse(Path(self.store.path).exists())

    def test_keyring_errors_do_not_echo_password(self):
        class BrokenKeyring:
            @staticmethod
            def set_password(_service, _username, _secret):
                raise RuntimeError("private-password-value")

        with patch.object(
            web_credential_store,
            "get_secure_keyring",
            return_value=BrokenKeyring,
        ):
            with self.assertRaises(WebCredentialStoreError) as error:
                self.store.save_login(
                    "https://replit.com",
                    "user@example.com",
                    "private-password-value",
                )
        self.assertNotIn("private-password-value", str(error.exception))
        self.assertFalse(Path(self.store.path).exists())


if __name__ == "__main__":
    unittest.main()
