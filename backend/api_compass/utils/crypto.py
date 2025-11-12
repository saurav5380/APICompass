from __future__ import annotations

import base64
import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from api_compass.core.config import settings


def _normalize_key(raw_key: str) -> bytes:
    """Return a Fernet-compatible key, deriving one if the provided string is not padded."""
    key_bytes = raw_key.encode("utf-8")
    try:
        # Validate the key eagerly; Fernet expects a urlsafe base64-encoded 32-byte key.
        base64.urlsafe_b64decode(key_bytes)
        return key_bytes
    except (base64.binascii.Error, ValueError):
        padded = key_bytes.ljust(32, b"\0")[:32]
        return base64.urlsafe_b64encode(padded)


@lru_cache
def _get_fernet() -> Fernet:
    key = settings.encryption_key.get_secret_value()
    return Fernet(_normalize_key(key))


def encrypt_bytes(payload: bytes) -> bytes:
    return _get_fernet().encrypt(payload)


def decrypt_bytes(token: bytes) -> bytes:
    return _get_fernet().decrypt(token)


def encrypt_auth_payload(payload: dict[str, Any]) -> bytes:
    return encrypt_bytes(json.dumps(payload).encode("utf-8"))


def try_decrypt_auth_payload(token: bytes) -> dict[str, Any] | None:
    try:
        data = decrypt_bytes(token)
    except InvalidToken:
        return None
    return json.loads(data.decode("utf-8"))


def mask_secret(secret: str, visible: int = 4) -> str:
    stripped = secret.strip()
    if not stripped:
        return "****"
    visible = max(1, visible)
    if len(stripped) <= visible:
        return "*" * len(stripped)
    hidden = "*" * (len(stripped) - visible)
    return f"{hidden}{stripped[-visible:]}"
