"""Armazena logins de sites no cofre seguro do sistema, nunca em arquivos."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from _ULTILIDADES_.site_utils import normalize_host
from _SERVICOS_.secure_keyring import SecureKeyringError, get_secure_keyring


SERVICE_KEYRING = "hen-nave.web-logins"
CONFIG_FILENAME = "web_logins.json"


class WebCredentialStoreError(RuntimeError):
    """Erro seguro para apresentar sem revelar senhas."""


def origin_for_url(url: str) -> str:
    """Retorna somente a origem HTTPS; rejeita URLs com credenciais embutidas."""
    try:
        parsed = urlsplit((url or "").strip())
        if (
            parsed.scheme.lower() != "https"
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError
        host = normalize_host(parsed.hostname)
        port = parsed.port
    except (TypeError, ValueError):
        raise WebCredentialStoreError(
            "Senhas só podem ser salvas para uma origem HTTPS válida."
        ) from None

    if not host:
        raise WebCredentialStoreError(
            "Senhas só podem ser salvas para uma origem HTTPS válida."
        )
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port_suffix = f":{port}" if port and port != 443 else ""
    return f"https://{host}{port_suffix}"


def _secret_json(username: str, password: str) -> str:
    return json.dumps(
        {"username": username, "password": password},
        ensure_ascii=False,
    )


def _decode_secret(secret: str) -> dict[str, str]:
    try:
        value = json.loads(secret)
    except (TypeError, json.JSONDecodeError):
        raise WebCredentialStoreError(
            "Um login salvo está inválido no cofre do sistema."
        ) from None
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("username"), str)
        or not isinstance(value.get("password"), str)
    ):
        raise WebCredentialStoreError(
            "Um login salvo está inválido no cofre do sistema."
        )
    return {"username": value["username"], "password": value["password"]}


class WebCredentialStore:
    """Metadados por origem em JSON; usuário e senha somente no keyring."""

    def __init__(self, config_directory: str | os.PathLike[str]):
        self.config_directory = Path(config_directory)
        self.path = self.config_directory / CONFIG_FILENAME

    def list_for_origin(self, url_or_origin: str) -> list[dict[str, str]]:
        origin = origin_for_url(url_or_origin)
        keyring = self._keyring()
        accounts = []
        for entry in self._load_entries():
            if entry["origin"] != origin:
                continue
            secret = self._get_secret(keyring, entry["id"])
            account = _decode_secret(secret)
            accounts.append(
                {"id": entry["id"], "username": account["username"]}
            )
        return accounts

    def get_login(self, credential_id: str, url_or_origin: str) -> dict[str, str]:
        origin = origin_for_url(url_or_origin)
        entry = next(
            (
                item
                for item in self._load_entries()
                if item["id"] == credential_id and item["origin"] == origin
            ),
            None,
        )
        if entry is None:
            raise WebCredentialStoreError(
                "Esse login não pertence ao site aberto."
            )
        return _decode_secret(self._get_secret(self._keyring(), credential_id))

    def save_login(
        self,
        url_or_origin: str,
        username: str,
        password: str,
    ) -> str:
        origin = origin_for_url(url_or_origin)
        username = str(username or "").strip()
        password = str(password or "")
        if not username:
            raise WebCredentialStoreError("Informe o e-mail ou usuário.")
        if not password:
            raise WebCredentialStoreError("Informe a senha.")
        if len(username) > 4096 or len(password) > 4096:
            raise WebCredentialStoreError("O login excede o tamanho permitido.")

        keyring = self._keyring()
        entries = self._load_entries()
        for entry in entries:
            if entry["origin"] != origin:
                continue
            saved = _decode_secret(self._get_secret(keyring, entry["id"]))
            if saved["username"] == username:
                try:
                    keyring.set_password(
                        SERVICE_KEYRING,
                        entry["id"],
                        _secret_json(username, password),
                    )
                except Exception:
                    raise WebCredentialStoreError(
                        "Não foi possível atualizar o login no cofre do sistema."
                    ) from None
                return entry["id"]

        credential_id = uuid.uuid4().hex
        try:
            keyring.set_password(
                SERVICE_KEYRING,
                credential_id,
                _secret_json(username, password),
            )
        except Exception:
            raise WebCredentialStoreError(
                "O cofre do sistema não aceitou o login. Nenhuma senha foi "
                "gravada em arquivo."
            ) from None

        entries.append({"id": credential_id, "origin": origin})
        try:
            self._write_entries(entries)
        except WebCredentialStoreError:
            try:
                keyring.delete_password(SERVICE_KEYRING, credential_id)
            except Exception:
                pass
            raise
        return credential_id

    def delete_login(self, credential_id: str, url_or_origin: str) -> None:
        origin = origin_for_url(url_or_origin)
        entries = self._load_entries()
        entry = next(
            (
                item
                for item in entries
                if item["id"] == credential_id and item["origin"] == origin
            ),
            None,
        )
        if entry is None:
            return

        keyring = self._keyring()
        secret = self._get_secret(keyring, credential_id, allow_missing=True)
        if secret is not None:
            try:
                keyring.delete_password(SERVICE_KEYRING, credential_id)
            except Exception:
                raise WebCredentialStoreError(
                    "Não foi possível remover a senha do cofre do sistema."
                ) from None

        remaining = [item for item in entries if item["id"] != credential_id]
        try:
            self._write_entries(remaining)
        except WebCredentialStoreError:
            if secret is not None:
                try:
                    keyring.set_password(SERVICE_KEYRING, credential_id, secret)
                except Exception:
                    pass
            raise

    def _load_entries(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise WebCredentialStoreError(
                "Não foi possível ler a lista de logins salvos."
            ) from None
        raw_entries = data.get("credentials") if isinstance(data, dict) else None
        if not isinstance(raw_entries, list):
            raise WebCredentialStoreError(
                "A lista de logins salvos tem um formato inválido."
            )

        entries = []
        seen_ids = set()
        for raw in raw_entries:
            if not isinstance(raw, dict):
                raise WebCredentialStoreError(
                    "A lista de logins salvos tem um formato inválido."
                )
            credential_id = str(raw.get("id") or "")
            try:
                origin = origin_for_url(str(raw.get("origin") or ""))
            except WebCredentialStoreError:
                raise WebCredentialStoreError(
                    "A lista de logins salvos contém um site inválido."
                ) from None
            if not credential_id or credential_id in seen_ids:
                raise WebCredentialStoreError(
                    "A lista de logins salvos contém um identificador inválido."
                )
            seen_ids.add(credential_id)
            entries.append({"id": credential_id, "origin": origin})
        return entries

    def _write_entries(self, entries: list[dict[str, str]]) -> None:
        temporary = self.path.with_name(
            f".{self.path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            self.config_directory.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(
                    {"version": 1, "credentials": entries},
                    stream,
                    indent=2,
                    ensure_ascii=False,
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except (OSError, TypeError, ValueError):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise WebCredentialStoreError(
                "Não foi possível salvar a lista de logins."
            ) from None

    @staticmethod
    def _keyring():
        try:
            return get_secure_keyring()
        except SecureKeyringError as error:
            raise WebCredentialStoreError(
                f"{error} Nenhuma senha foi salva em arquivo."
            ) from None

    @staticmethod
    def _get_secret(keyring, credential_id: str, *, allow_missing: bool = False):
        try:
            secret = keyring.get_password(SERVICE_KEYRING, credential_id)
        except Exception:
            raise WebCredentialStoreError(
                "Não foi possível acessar o cofre do sistema."
            ) from None
        if secret is None and not allow_missing:
            raise WebCredentialStoreError(
                "A senha salva não está no cofre do sistema. Remova e salve o "
                "login novamente."
            )
        return secret
