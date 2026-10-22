import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core import get_settings

SESSION_COOKIE = "poopr_session"
OAUTH_STATE_COOKIE = "poopr_oauth_state"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(value: str) -> str:
    secret = get_settings().session_secret.encode()
    return _b64encode(hmac.new(secret, value.encode(), hashlib.sha256).digest())


def create_session_token(email: str) -> str:
    payload = {
        "email": email.strip().lower(),
        "exp": int(time.time()) + SESSION_MAX_AGE_SECONDS,
    }
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{encoded_payload}.{_sign(encoded_payload)}"


def read_session_token(token: str | None) -> str | None:
    if not token or "." not in token:
        return None

    encoded_payload, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(encoded_payload)):
        return None

    try:
        payload: dict[str, Any] = json.loads(_b64decode(encoded_payload))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None

    email = payload.get("email")
    if not email:
        return None
    return str(email).strip().lower()
