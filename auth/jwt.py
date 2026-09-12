from datetime import datetime, timedelta, timezone
import os

from fastapi import HTTPException
from jose import JWTError, jwt

ALGO = "HS256"


def _secret() -> str:
    value = os.getenv("JWT_SECRET", "")
    if not value:
        raise RuntimeError("JWT_SECRET missing")
    return value


def create_access_token(sub: str, role: str, expires_minutes: int = 120) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGO)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGO])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
