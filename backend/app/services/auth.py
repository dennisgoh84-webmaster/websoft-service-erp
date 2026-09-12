"""Minimal authentication: password hashing + JWT issuance/verification.

This is a demo-scale implementation of the "Authentication and
role-based permissions are required" development rule -- enough to
gate the API and know who is acting (for audit trails), while the
detailed role/permission catalogue (open item 8.4) remains to be
designed.

Extended 2026-09-12 with: password complexity, a forced-change-on-
first-login flow, and email OTP as a second factor (see
app/routers/auth.py for the full login sequence). Every JWT this module
issues carries a "purpose" claim -- "access" for a normal API bearer
token, "password_change" / "otp" for the two short-lived intermediate
tokens those flows hand back -- so a change/OTP token can never be
replayed as a real access token even if it leaked, and `decode_access_token`
rejects anything that isn't purpose="access".
"""
import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# Confirmed 2026-09-12: "staff password have to use complex password like
# alphanumeric" -- at least one letter and one digit, on top of the
# 8-character minimum the schemas already enforced. No uppercase/
# special-character rule was given, so none is assumed.
MIN_PASSWORD_LENGTH = 8


def validate_password_complexity(password: str) -> None:
    """Raises ValueError (caught by callers and turned into a 422) if the
    password doesn't meet policy. Called from every place a password is
    set: user creation, admin reset, self-service change."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number.")


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "purpose": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def create_purpose_token(
    user_id: uuid.UUID, purpose: str, *, expire_minutes: int, extra: dict | None = None
) -> str:
    """A short-lived token for one specific next step (finishing a forced
    password change, or completing an OTP challenge) -- never accepted by
    `get_current_user` since its purpose isn't "access"."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "purpose": purpose, **(extra or {})}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_purpose_token(token: str, expected_purpose: str) -> dict | None:
    """Returns the token's payload (including `sub` as a string, and
    whatever `extra` fields were set) if it's valid and matches the
    expected purpose; None otherwise."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != expected_purpose:
            return None
        uuid.UUID(payload["sub"])  # validate shape without discarding the rest
        return payload
    except (JWTError, KeyError, ValueError):
        return None
