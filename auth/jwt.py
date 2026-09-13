"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a."""
import hmac
import os
import time

import jwt

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 8 * 60 * 60

DEMO_USERS = {
    "tracker": {"password": "track123", "role": "tracker"},
    "analyst": {"password": "analytics123", "role": "analyst"},
}


def authenticate(username: str, password: str) -> str | None:
    user = DEMO_USERS.get(username)
    if not user or not hmac.compare_digest(user["password"], password):
        return None
    payload = {
        "sub": username,
        "role": user["role"],
        "exp": int(time.time()) + JWT_TTL_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
