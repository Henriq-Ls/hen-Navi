import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import _SERVICOS_.ai_provider_store as ai_provider_store
from _SERVICOS_.ai_provider_store import ProviderStore, ProviderStoreError

_ORIGINAL_SAFE_KEYRING = ai_provider_store._safe_keyring


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


class ProviderStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ProviderStore(self.temp.name)
        self.keyring_patch = patch.object(ai_provider_store, "_safe_keyring", return_value=FakeKeyring)
        self.keyring_patch.start()
        self.addCleanup(self.keyring_patch.stop)
        FakeKeyring.secrets.clear()

    def provider(self, **overrides):
        value = {
            "id": "provider-one",
            "name": "Meu provedor",
            "kind": "openai_compatible",
            "platform": "custom",
            "base_url": "https://api.example/v1",
            "model": "model-1",
            "max_page_chars": 12000,
        }
        value.update(overrides)
        return value

    def test_secret_is_stored_outside_metadata_file(self):
        saved = self.store.save_provider(self.provider(), secret="sensitive-token")
        contents = Path(self.store.path).read_text(encoding="utf-8")
        self.assertNotIn("sensitive-token", contents)
        self.assertIn("credential_id", json.loads(contents)["providers"][0])
        self.assertEqual(self.store.get_secret(saved), "sensitive-token")

    def test_edit_without_secret_keeps_existing_key(self):
        saved = self.store.save_provider(self.provider(), secret="secret-one")
        edited = self.store.save_provider(self.provider(name="Nome alterado"))
        self.assertEqual(edited["credential_id"], saved["credential_id"])
        self.assertEqual(self.store.get_secret(edited), "secret-one")

    def test_replace_secret_rotates_keyring_id_without_plaintext(self):
        old = self.store.save_provider(self.provider(), secret="old-secret")
        new = self.store.save_provider(self.provider(), secret="new-secret")
        self.assertNotEqual(old["credential_id"], new["credential_id"])
        self.assertEqual(self.store.get_secret(new), "new-secret")
        self.assertNotIn(
            ("hen-nave.ai", old["credential_id"]),
            FakeKeyring.secrets,
        )
        self.assertNotIn("new-secret", Path(self.store.path).read_text(encoding="utf-8"))

    def test_remove_provider_updates_active_connection(self):
        first = self.store.save_provider(self.provider(), secret="one")
        self.store.save_provider(
            self.provider(id="provider-two", name="Outro", base_url="https://two.example"),
            secret="two",
        )
        self.store.set_active("provider-two")
        self.store.remove_provider("provider-two")
        data = self.store.load()
        self.assertEqual(data["active_id"], first["id"])
        self.assertEqual([p["id"] for p in data["providers"]], [first["id"]])

    def test_missing_keyring_backend_fails_without_file_fallback(self):
        with patch.object(
            ai_provider_store,
            "_safe_keyring",
            side_effect=ProviderStoreError("keyring indisponível"),
        ):
            with self.assertRaises(ProviderStoreError):
                self.store.save_provider(self.provider(), secret="secret")
        self.assertFalse(Path(self.store.path).exists())

    def test_insecure_keyring_backend_is_rejected(self):
        insecure_module = types.ModuleType("keyring")

        class InsecureBackend:
            __module__ = "keyrings.alt.file"

        insecure_module.get_keyring = lambda: InsecureBackend()
        with patch.dict(sys.modules, {"keyring": insecure_module}):
            with self.assertRaisesRegex(ProviderStoreError, "não é um cofre seguro"):
                _ORIGINAL_SAFE_KEYRING()

    def test_keyring_errors_do_not_echo_the_secret(self):
        class BrokenKeyring:
            @staticmethod
            def set_password(_service, _username, _secret):
                raise RuntimeError("token-to-never-show")

        with patch.object(
            ai_provider_store,
            "_safe_keyring",
            return_value=BrokenKeyring,
        ):
            with self.assertRaises(ProviderStoreError) as error:
                self.store.save_provider(
                    self.provider(),
                    secret="token-to-never-show",
                )
        self.assertNotIn("token-to-never-show", str(error.exception))
        self.assertFalse(Path(self.store.path).exists())

    def test_metadata_loader_does_not_expose_unknown_fields(self):
        Path(self.store.path).write_text(
            json.dumps({
                "active_id": "provider-one",
                "providers": [
                    {
                        **self.provider(),
                        "api_key": "should-not-survive",
                        "secret": "should-not-survive-either",
                    }
                ],
            }),
            encoding="utf-8",
        )
        loaded = self.store.load()
        text = json.dumps(loaded)
        self.assertNotIn("should-not-survive", text)
        self.assertNotIn("api_key", loaded["providers"][0])


if __name__ == "__main__":
    unittest.main()
