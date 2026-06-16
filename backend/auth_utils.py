"""
auth_utils.py — JWT token creation/validation and password hashing.

Backward-compatible:
  • verify_password() handles BOTH legacy plaintext passwords (existing
    admin/owner accounts) AND bcrypt-hashed passwords (new tenant accounts).
  • System tenant (demo accounts) can keep plaintext passwords so they don't
    need migration.  New tenant passwords are always bcrypt-hashed at creation.

Uses `bcrypt` library directly (not passlib) for Python 3.12 compatibility.
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Optional

SECRET_KEY: str     = os.environ.get("JWT_SECRET",
                          "cafe-buddy-jwt-secret-change-in-production")
ALGORITHM: str      = "HS256"
TOKEN_EXPIRE_H: int = 24     # tokens valid for 24 hours


# ── Password helpers ───────────────────────────────────────────────────────────
# Use `bcrypt` directly — passlib 1.7.4 has a known incompatibility with
# bcrypt ≥4.x on Python 3.12.
try:
    import bcrypt as _bcrypt_lib
    _HAS_BCRYPT = True
except ImportError:
    _bcrypt_lib = None   # type: ignore
    _HAS_BCRYPT = False


def hash_password(password: str) -> str:
    """Return bcrypt hash of password. Falls back to plaintext if bcrypt unavailable."""
    if _HAS_BCRYPT:
        pw_bytes = password.encode("utf-8")
        return _bcrypt_lib.hashpw(pw_bytes, _bcrypt_lib.gensalt()).decode("utf-8")
    return password   # graceful fallback during local dev without bcrypt


def verify_password(plain: str, stored: str) -> bool:
    """
    Verify a password against its stored form.
    Handles legacy plaintext (starts with anything other than $2b/$2a/$2y)
    and modern bcrypt hashes transparently.
    """
    if stored.startswith(("$2b$", "$2a$", "$2y$")):
        if _HAS_BCRYPT:
            try:
                return _bcrypt_lib.checkpw(
                    plain.encode("utf-8"),
                    stored.encode("utf-8"),
                )
            except Exception:
                return False
        return False   # can't verify bcrypt without the library
    return plain == stored   # legacy plaintext comparison


# ── JWT helpers ────────────────────────────────────────────────────────────────
try:
    from jose import JWTError, jwt as _jwt  # noqa: F401
    _HAS_JOSE = True
except ImportError:
    _jwt = None       # type: ignore
    _HAS_JOSE = False


def create_access_token(data: dict, expires_hours: int = TOKEN_EXPIRE_H) -> str:
    """
    Create a signed JWT token carrying the supplied data dict plus an `exp` claim.
    Falls back to a simple deterministic string token if python-jose is unavailable.
    """
    if not _HAS_JOSE:
        # Fallback: old-style demo token
        return f"demo-token-{data.get('username', 'user')}"

    payload = dict(data)
    payload["exp"] = datetime.utcnow() + timedelta(hours=expires_hours)
    return _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.  Returns the payload dict or None if
    invalid / expired.  Never raises.
    """
    if not _HAS_JOSE:
        return None
    try:
        return _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


def extract_tenant_id(authorization_header: str) -> Optional[str]:
    """
    Given the value of an Authorization header, extract the tenant_id from
    the embedded JWT payload.  Returns None for legacy / unauthenticated calls.

    Expected format:  Authorization: Bearer <token>
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return None
    token = authorization_header[7:].strip()
    payload = decode_token(token)
    if payload:
        return payload.get("tenant_id")
    return None


def extract_username(authorization_header: str) -> Optional[str]:
    """Extract username from JWT Bearer token."""
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return None
    token = authorization_header[7:].strip()
    payload = decode_token(token)
    if payload:
        return payload.get("username")
    return None
