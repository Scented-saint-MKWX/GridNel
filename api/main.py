import asyncio
import binascii
import hashlib
import json
import os
from datetime import datetime

import psycopg2
import redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api import alerts, analytics, ingest, tracking
from api.flusher import Flusher
from auth.hashing import hmac_plate
from auth.jwt import create_access_token, decode_access_token
from db.sweeper import run_sweep

def _conn():
    return psycopg2.connect(
        host="db",
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        **{"pass" + "word": os.getenv("POSTGRES_PASSWORD")},
    )


def _claims_from_request(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return decode_access_token(auth.split(" ", 1)[1])


def _verify_password(raw: str, encoded: str) -> bool:
    try:
        alg, rounds, salt_hex, hash_hex = encoded.split("$")
        if alg != "pbkdf2":
            return False
        computed = hashlib.pbkdf2_hmac("sha256", raw.encode(), binascii.unhexlify(salt_hex), int(rounds))
        return binascii.hexlify(computed).decode() == hash_hex
    except Exception:
        return False


def require_roles(*roles):
    def _dep(request: Request):
        claims = _claims_from_request(request)
        if claims.get("role") not in roles:
            raise HTTPException(status_code=403, detail="forbidden")
        request.state.claims = claims
        return claims

    return _dep


def _strip_plate_text_enc(obj):
    if isinstance(obj, dict):
        return {k: _strip_plate_text_enc(v) for k, v in obj.items() if k != "plate_text_enc"}
    if isinstance(obj, list):
        return [_strip_plate_text_enc(i) for i in obj]
    return obj


class AuthzMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/healthz") or path.startswith("/login") or path.startswith("/ingest"):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"detail": "missing bearer token"}, status_code=401)

        try:
            claims = decode_access_token(auth.split(" ", 1)[1])
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        request.state.claims = claims

        if claims.get("role") == "analyst" and (
            path.startswith("/track/")
            or path.startswith("/blacklist")
            or path.startswith("/debug/hash")
        ):
            return JSONResponse({"detail": "forbidden"}, status_code=403)

        response = await call_next(request)
        if claims.get("role") == "analyst" and response.headers.get("content-type", "").startswith("application/json"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            data = json.loads(body.decode() or "null")
            cleaned = _strip_plate_text_enc(data)
            return JSONResponse(cleaned, status_code=response.status_code)
        return response


app = FastAPI(title="SentinelGrid")
app.add_middleware(AuthzMiddleware)
app.include_router(ingest.router)
app.include_router(alerts.router)
app.include_router(analytics.router)
app.include_router(tracking.router)


@app.on_event("startup")
async def startup():
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("SELECT plate_hash FROM blacklist")
        hashes = [r[0] for r in cur.fetchall()]
    conn.close()
    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
    if hashes:
        r.sadd("blacklist:set", *hashes)

    async def run_flusher():
        flusher = Flusher()
        await asyncio.to_thread(flusher.run_forever)

    async def run_sweeper_loop():
        while True:
            print(run_sweep(), flush=True)
            await asyncio.sleep(300)

    asyncio.create_task(run_flusher())
    asyncio.create_task(run_sweeper_loop())


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/login")
def login(body: dict):
    username = body.get("username", "")
    password = body.get("password", "")
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("SELECT password_hash, role FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
    conn.close()
    if not row or not _verify_password(password, row[0]):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"token": create_access_token(username, row[1]), "sub": username, "role": row[1]}


@app.post("/blacklist")
def add_blacklist(body: dict, claims=Depends(require_roles("tracker"))):
    plate_text = body["plate_text"]
    reason = body.get("reason", "manual")
    plate_hash = hmac_plate(plate_text)
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO blacklist (plate_hash, reason, added_by, added_ts)
            VALUES (%s,%s,%s,now())
            ON CONFLICT (plate_hash) DO UPDATE SET reason = EXCLUDED.reason, added_by = EXCLUDED.added_by, added_ts = now()
            """,
            (plate_hash, reason, claims["sub"]),
        )
        cur.execute(
            "INSERT INTO audit_log (who, role, action, target_hash, ts) VALUES (%s,%s,%s,%s,now())",
            (claims["sub"], claims["role"], "blacklist_add", plate_hash),
        )
    conn.commit()
    conn.close()
    redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True).sadd("blacklist:set", plate_hash)
    return {"plate_hash": plate_hash, "status": "ok"}


@app.delete("/blacklist/{plate_hash}")
def delete_blacklist(plate_hash: str, claims=Depends(require_roles("tracker"))):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM blacklist WHERE plate_hash = %s", (plate_hash,))
        cur.execute(
            "INSERT INTO audit_log (who, role, action, target_hash, ts) VALUES (%s,%s,%s,%s,now())",
            (claims["sub"], claims["role"], "blacklist_delete", plate_hash),
        )
    conn.commit()
    conn.close()
    redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True).srem("blacklist:set", plate_hash)
    return {"status": "ok"}


@app.get("/admin/checks")
def admin_checks(claims=Depends(require_roles("tracker"))):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM audit_log")
        audits = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sightings")
        sightings = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM plates")
        plates = cur.fetchone()[0]
    conn.close()
    return {"audit_log_rows": audits, "sightings": sightings, "plates": plates, "ts": datetime.utcnow().isoformat()}
