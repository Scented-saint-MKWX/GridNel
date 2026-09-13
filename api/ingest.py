"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
POST /ingest per TEAM.md §4/§8: validate -> SETNX dedupe (5s) -> blacklist
check (alert path, never skipped) -> XADD sightings:stream. Never INSERT to
Postgres directly here — the flusher owns that.
"""
import hmac
import json
import os

from fastapi import APIRouter, Header, HTTPException

from api.models import get_redis
from api.schemas import DataBlock

router = APIRouter()

FOG_API_KEY = os.environ["FOG_API_KEY"]


@router.post("/ingest", tags=["Ingestion"])
def ingest_data(block: DataBlock, x_fog_api_key: str | None = Header(default=None)):
    # fog_sim.py (P2's own file) sends X-Fog-Api-Key, not Authorization —
    # matching its already-established convention rather than inventing a
    # second one here.
    if not hmac.compare_digest(x_fog_api_key or "", FOG_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid fog API key")

    r = get_redis()

    dedupe_key = f"dedup:{block.camera_id}:{block.plate_hash}"
    if not r.set(dedupe_key, "1", nx=True, ex=5):
        return {"status": "duplicate"}

    alert = False
    if r.sismember("blacklist", block.plate_hash):
        alert = True
        r.xadd(
            "alerts:stream",
            {
                "type": "blacklist_hit",
                "plate_hash": block.plate_hash,
                "camera_id": block.camera_id,
                "ts": block.ts,
                "detail": json.dumps({"reason": "blacklist match"}),
            },
        )

    r.xadd(
        "sightings:stream",
        {
            "plate_hash": block.plate_hash,
            "plate_text_enc": block.plate_text_enc,
            "camera_id": block.camera_id,
            "ts": block.ts,
            "conf": block.conf,
            "outcome": block.resolution.outcome,
            "alt_hashes": json.dumps(block.resolution.alt_hashes),
            "quality": block.quality,
        },
    )

    return {"status": "accepted", "alert": alert}
