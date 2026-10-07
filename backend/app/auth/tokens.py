import base64
import hashlib
import hmac
import json
import time


def _encode(value: dict[str, object], secret: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=").decode()
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return payload + "." + base64.urlsafe_b64encode(signature).rstrip(b"=").decode()


def issue_token(subject: str, secret: str, expires_in: int = 3600) -> str:
    return _encode({"sub": subject, "exp": int(time.time()) + expires_in}, secret)


def verify_token(token: str, secret: str) -> str | None:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(actual, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) <= int(time.time()):
            return None
        return str(data["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
