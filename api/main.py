"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
App factory + routers, per TEAM.md §8 P4 spec.
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api import alerts, analytics, ingest, tracking
from api.schemas import LoginRequest
from auth.jwt import authenticate

app = FastAPI(title="SentinelGrid API")

# Not a wildcard — auth is a Bearer JWT (no ambient cookie credential), but an
# unrestricted allow_origins still lets any page that has obtained a token
# call this API cross-origin with no check. Pin to the actual frontend origin.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Fog-Api-Key"],
)

app.include_router(ingest.router)
app.include_router(tracking.router)
app.include_router(alerts.router)
app.include_router(analytics.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/login")
def login(body: LoginRequest):
    token = authenticate(body.username, body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": token}
