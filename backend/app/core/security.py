import os
from datetime import UTC, datetime, timedelta

import jwt
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set in the environment (.env)")
# RFC 7518 3.2: an HS256 key must be at least 256 bits. Generate one with:
#   python -c "import secrets; print(secrets.token_hex(32))"
if len(JWT_SECRET.encode()) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 bytes long")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours, configurable here rather than hardcoded in callers

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=expires_minutes)
    # iat lets the API reject tokens issued before a password change (User.token_is_current).
    # Sub-second iat (RFC 7519 allows non-integer NumericDate), so a token issued
    # a moment before a password change in the same second is still rejected.
    payload = {"sub": subject, "role": role, "iat": now.timestamp(), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
