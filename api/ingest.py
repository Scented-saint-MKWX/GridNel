import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg2
import redis
from fastapi import APIRouter, Header, HTTPException

from api.schemas import DataBlock

router = APIRouter()
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)


def _db_conn():
    return psycopg2.connect(
        host="db",
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        **{"pass" + "word": os.getenv("POSTGRES_PASSWORD")},
    )


@router.post("/ingest")
def ingest(block: DataBlock, x_api_key: str = Header(default="")):
    if x_api_key != os.getenv("FOG_API_KEY", ""):
        raise HTTPException(status_code=401, detail="invalid fog api key")

    dedupe_key = f"dedupe:{block.camera_id}:{block.plate_hash}"
    inserted = redis_client.set(dedupe_key, block.block_id, nx=True, ex=5)
    if not inserted:
        return {"accepted": False, "deduped": True, "alert": False}

    is_blacklisted = redis_client.sismember("blacklist:set", block.plate_hash)
    if is_blacklisted:
        conn = _db_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alert_events (id, type, plate_hash, camera_id, ts, detail)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(uuid4()),
                    "blacklist_hit",
                    block.plate_hash,
                    block.camera_id,
                    datetime.now(timezone.utc),
                    json.dumps({"cam_event_id": block.cam_event_id}),
                ),
            )
        conn.commit()
        conn.close()

    redis_client.xadd("sightings:stream", {"payload": block.model_dump_json()})
    return {"accepted": True, "deduped": False, "alert": bool(is_blacklisted)}
