from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet


class SecretCipher:
    def __init__(self, master_key: str) -> None:
        key_bytes = master_key.encode("utf-8")
        self._fernet = Fernet(key_bytes)

    @classmethod
    def from_env(cls) -> "SecretCipher":
        existing = os.getenv("MEA_MASTER_KEY")
        if existing is not None:
            try:
                return cls(existing)
            except Exception:
                pass
        generated = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
        return cls(generated)

    def encrypt(self, plain_text: str) -> str:
        return self._fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_text: str) -> str:
        return self._fernet.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
