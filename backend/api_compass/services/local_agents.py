from __future__ import annotations

import base64
import hmac
import secrets
from datetime import datetime, timezone

from api_compass.utils.crypto import encrypt_auth_payload, try_decrypt_auth_payload

_MODE_KEY = "local_agent"
_TOKEN_PREFIX = "lc_"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def generate_agent_token() -> str:
    suffix = secrets.token_urlsafe(32)
    return f"{_TOKEN_PREFIX}{suffix}"


def build_auth_blob(agent_token: str) -> bytes:
    payload = {
        "mode": _MODE_KEY,
        "agent_token": agent_token,
        "issued_at": _now_iso(),
    }
    return encrypt_auth_payload(payload)


def extract_agent_token(encrypted_blob: bytes) -> str | None:
    payload = try_decrypt_auth_payload(encrypted_blob)
    if not payload:
        return None
    if payload.get("mode") != _MODE_KEY:
        return None
    token = payload.get("agent_token")
    if not isinstance(token, str):
        return None
    return token


def token_preview(agent_token: str) -> str:
    if not agent_token:
        return "local-agent"
    visible = agent_token[-4:]
    return f"local-agent:*{visible}"


def sign_payload(agent_token: str, body: bytes) -> str:
    digest = hmac.new(agent_token.encode("utf-8"), body, digestmod="sha256").digest()
    encoded = base64.urlsafe_b64encode(digest).decode("utf-8")
    return encoded.rstrip("=")


def verify_signature(agent_token: str, provided_signature: str | None, body: bytes) -> bool:
    if not provided_signature:
        return False
    expected = sign_payload(agent_token, body)
    normalized = provided_signature.strip()
    if not normalized:
        return False
    normalized = normalized.rstrip("=")
    return hmac.compare_digest(expected, normalized)
