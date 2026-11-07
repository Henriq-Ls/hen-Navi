"""Persistência de conexões de IA sem armazenar credenciais em arquivos."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from _CONFIGURA_ import (
    LIMITE_CARACTERES_PAGINA_IA,
    LIMITE_CARACTERES_PAGINA_IA_MAXIMO,
    LIMITE_CARACTERES_PAGINA_IA_MINIMO,
)
from _SERVICOS_.secure_keyring import SecureKeyringError, get_secure_keyring

SERVICE_KEYRING = "hen-nave.ai"
CONFIG_FILENAME = "ai_providers.json"
class ProviderStoreError(RuntimeError):
    """Erro seguro para apresentar ao usuário, sem conteúdo de credenciais."""


def _safe_keyring():
    try:
        return get_secure_keyring()
    except SecureKeyringError as error:
        if str(error) == "O keyring do sistema não está disponível.":
            raise ProviderStoreError(
                "O keyring do sistema não está disponível. Nenhuma chave foi salva."
            ) from None
        raise ProviderStoreError(
            f"{error} Configure um keyring do Windows, macOS ou Linux e tente novamente."
        ) from None



class ProviderStore:
    """Guarda metadados no AppData e tokens em um cofre seguro do sistema."""

    def __init__(self, config_directory: str | os.PathLike[str]):
        self.config_directory = Path(config_directory)
        self.path = self.config_directory / CONFIG_FILENAME

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "active_id": "", "providers": []}
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise ProviderStoreError(
                "Não foi possível ler as conexões de IA. O arquivo de configuração "
                "não foi alterado."
            ) from None
        if not isinstance(data, dict) or not isinstance(data.get("providers"), list):
            raise ProviderStoreError(
                "O arquivo de conexões de IA tem um formato inválido."
            )
        providers = [
            self._public_provider(item)
            for item in data["providers"]
            if isinstance(item, dict)
        ]
        active_id = str(data.get("active_id") or "")
        if active_id not in {item["id"] for item in providers}:
            active_id = ""
        return {"version": 1, "active_id": active_id, "providers": providers}

    def active_provider(self) -> dict[str, Any] | None:
        data = self.load()
        return next(
            (item for item in data["providers"] if item["id"] == data["active_id"]),
            None,
        )

    def get_provider(self, provider_id: str) -> dict[str, Any] | None:
        data = self.load()
        return next((p for p in data["providers"] if p["id"] == provider_id), None)

    def get_secret(self, provider: dict[str, Any]) -> str:
        credential_id = str(provider.get("credential_id") or "")
        if not credential_id:
            return ""
        keyring = _safe_keyring()
        try:
            secret = keyring.get_password(SERVICE_KEYRING, credential_id)
        except Exception:
            raise ProviderStoreError(
                "Não foi possível acessar a chave no keyring do sistema."
            ) from None
        if secret is None:
            raise ProviderStoreError(
                "A chave desta conexão não está no keyring. Edite a conexão e "
                "cadastre a chave novamente."
            )
        return secret

    def save_provider(
        self,
        provider: dict[str, Any],
        *,
        secret: str = "",
        remove_secret: bool = False,
    ) -> dict[str, Any]:
        clean = self._public_provider(provider)
        existing = self.get_provider(clean["id"])
        old_credential_id = str((existing or {}).get("credential_id") or "")
        new_credential_id = old_credential_id
        secret_was_written = False

        if secret:
            keyring = _safe_keyring()
            new_credential_id = uuid.uuid4().hex
            try:
                keyring.set_password(SERVICE_KEYRING, new_credential_id, secret)
            except Exception:
                raise ProviderStoreError(
                    "O keyring do sistema não aceitou a chave. "
                    "Nenhuma chave foi gravada em arquivo."
                ) from None
            secret_was_written = True
        elif remove_secret:
            new_credential_id = ""

        clean["credential_id"] = new_credential_id
        data = self.load()
        providers = [p for p in data["providers"] if p["id"] != clean["id"]]
        providers.append(clean)
        active_id = data["active_id"] or clean["id"]
        try:
            self._write({"version": 1, "active_id": active_id, "providers": providers})
        except ProviderStoreError:
            if secret_was_written:
                self._delete_credential(new_credential_id, ignore_errors=True)
            raise

        if old_credential_id and old_credential_id != new_credential_id:
            self._delete_credential(old_credential_id, ignore_errors=False)
        return clean

    def set_active(self, provider_id: str) -> None:
        data = self.load()
        if provider_id and provider_id not in {p["id"] for p in data["providers"]}:
            raise ProviderStoreError("A conexão selecionada não existe.")
        data["active_id"] = provider_id
        self._write(data)

    def set_cloud_warning_dismissed(self, provider_id: str, dismissed: bool) -> None:
        data = self.load()
        for provider in data["providers"]:
            if provider["id"] == provider_id:
                provider["suppress_cloud_warning"] = bool(dismissed)
                break
        self._write(data)

    def remove_provider(self, provider_id: str) -> None:
        data = self.load()
        removed = next(
            (p for p in data["providers"] if p["id"] == provider_id),
            None,
        )
        if removed is None:
            return
        data["providers"] = [p for p in data["providers"] if p["id"] != provider_id]
        if data["active_id"] == provider_id:
            data["active_id"] = data["providers"][0]["id"] if data["providers"] else ""
        self._write(data)
        credential_id = str(removed.get("credential_id") or "")
        if credential_id:
            self._delete_credential(credential_id, ignore_errors=False)

    def _delete_credential(self, credential_id: str, *, ignore_errors: bool) -> None:
        try:
            _safe_keyring().delete_password(SERVICE_KEYRING, credential_id)
        except Exception:
            if not ignore_errors:
                raise ProviderStoreError(
                    "A conexão foi atualizada, mas não foi possível remover uma "
                    "credencial antiga do keyring. Revise o cofre do sistema."
                ) from None

    @staticmethod
    def _public_provider(provider: dict[str, Any]) -> dict[str, Any]:
        provider_id = str(provider.get("id") or uuid.uuid4().hex)
        kind = str(provider.get("kind") or "openai_compatible")
        if kind not in {"ollama", "openai_compatible"}:
            raise ProviderStoreError("O tipo de conexão de IA não é suportado.")
        name = str(provider.get("name") or "").strip()
        base_url = str(provider.get("base_url") or "").strip()
        model = str(provider.get("model") or "").strip()
        if not name or not base_url:
            raise ProviderStoreError("Informe um nome e uma URL base.")
        try:
            page_limit = int(provider.get("max_page_chars", LIMITE_CARACTERES_PAGINA_IA))
        except (TypeError, ValueError):
            page_limit = LIMITE_CARACTERES_PAGINA_IA
        page_limit = min(
            max(page_limit, LIMITE_CARACTERES_PAGINA_IA_MINIMO),
            LIMITE_CARACTERES_PAGINA_IA_MAXIMO,
        )
        return {
            "id": provider_id,
            "name": name[:80],
            "kind": kind,
            "platform": str(provider.get("platform") or kind)[:40],
            "base_url": base_url[:2048],
            "model": model[:300],
            "max_page_chars": page_limit,
            "credential_id": str(provider.get("credential_id") or ""),
            "suppress_cloud_warning": bool(
                provider.get("suppress_cloud_warning", False)
            ),
        }

    def _write(self, data: dict[str, Any]) -> None:
        try:
            self.config_directory.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".json.tmp")
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            raise ProviderStoreError(
                "Não foi possível salvar as conexões de IA no AppData."
            ) from None
