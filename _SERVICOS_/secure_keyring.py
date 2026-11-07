"""Acesso somente a cofres de credenciais protegidos pelo sistema operacional."""

from __future__ import annotations


_SAFE_KEYRING_MODULES = (
    "keyring.backends.Windows",
    "keyring.backends.macOS",
    "keyring.backends.SecretService",
    "keyring.backends.kwallet",
)


class SecureKeyringError(RuntimeError):
    """O cofre seguro do sistema não está disponível."""


def get_secure_keyring():
    try:
        import keyring

        backend = keyring.get_keyring()
    except Exception:
        raise SecureKeyringError(
            "O keyring do sistema não está disponível."
        ) from None

    module = type(backend).__module__
    if not any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in _SAFE_KEYRING_MODULES
    ):
        raise SecureKeyringError(
            "O keyring selecionado não é um cofre seguro do sistema."
        )
    return keyring
