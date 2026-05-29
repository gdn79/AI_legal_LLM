import hashlib
import hmac
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
import json

from app.core.config import get_settings


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    salt_hex, digest_hex = password_hash.split(":")
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000
    )
    return hmac.compare_digest(candidate.hex(), digest_hex)


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    expires_at = int((datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)).timestamp())
    payload = {"sub": subject, "role": role, "exp": expires_at}
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")
    encoded_payload = urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{signing_input}.{encoded_signature}"


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
    signing_input = f"{encoded_header}.{encoded_payload}"
    expected = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_signature = urlsafe_b64encode(expected).decode("utf-8").rstrip("=")
    if not hmac.compare_digest(encoded_signature, expected_signature):
        raise ValueError("Invalid token signature")
    padded_payload = encoded_payload + "=" * (-len(encoded_payload) % 4)
    payload = json.loads(urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8"))
    if payload["exp"] < int(datetime.now(UTC).timestamp()):
        raise ValueError("Token expired")
    return payload
