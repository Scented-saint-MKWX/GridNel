"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
Role-gating dependency: analyst -> /track* and blacklist mutations = 403,
per TEAM.md §8 P5 spec. plate_text_enc stripping happens at the response
model level (analytics/tracking never emit it to begin with in this build —
see DECISIONS.md #7a note on scope), not via middleware post-processing.
"""
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.jwt import verify

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return verify(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_role(role: str):
    def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != role:
            raise HTTPException(status_code=403, detail="Forbidden for this role")
        return user

    return _dep


def require_any_role(user: dict = Depends(get_current_user)) -> dict:
    return user
