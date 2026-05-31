import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _encode(payload: dict[str, Any], ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    data = {**payload, "iat": now, "exp": now + ttl}
    return jwt.encode(data, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def make_access_token(user_id: uuid.UUID, role: str) -> str:
    return _encode(
        {"sub": str(user_id), "role": role, "typ": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_TTL_MIN),
    )


def make_refresh_token(user_id: uuid.UUID) -> str:
    return _encode(
        {"sub": str(user_id), "typ": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
    )


def make_ws_ticket(user_id: uuid.UUID) -> str:
    return _encode(
        {"sub": str(user_id), "typ": "ws"},
        timedelta(seconds=settings.WS_TICKET_TTL_SEC),
    )


def make_device_token(device_id: uuid.UUID, serial_id: str) -> str:
    return _encode(
        {"sub": str(device_id), "serial": serial_id, "typ": "device"},
        timedelta(days=settings.DEVICE_TOKEN_TTL_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except JWTError as e:
        raise ValueError(f"invalid token: {e}") from e
