import os
import hmac
import redis
from fastapi import HTTPException
from .schemas import DataBlock

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FOG_API_KEY = os.getenv("FOG_API_KEY", "hackathon_secret_key")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def authenticate_fog(api_key: str):
    if not hmac.compare_digest(api_key, FOG_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid fog API key")

def is_duplicate(block: DataBlock):
    key = f"dedup:{block.camera_id}:{block.plate_text}"
    created = redis_client.set(key, "1", nx=True, ex=5)
    return not created

def ingest_block(block: DataBlock, api_key: str):
    authenticate_fog(api_key)
    
    if is_duplicate(block):
        return {"status": "discarded", "reason": "duplicate", "block_id": block.block_id}

    # Store in Redis Stream (Plaintext version)
    redis_client.xadd(
        "sightings:stream",
        {
            "block_id": block.block_id,
            "camera_id": block.camera_id,
            "cam_event_id": block.cam_event_id,
            "ts": block.ts.isoformat(), # Fixed for Redis
            "plate_text": block.plate_text, # Plaintext
            "conf": str(block.conf),
            "lat": str(block.location.lat),
            "lon": str(block.location.lon),
            "fused_as": block.resolution.fused_as,
            "outcome": block.resolution.outcome,
            "vendor_guess": block.resolution.vendor_guess or "",
            "alt_texts": ",".join(block.resolution.alt_hashes),
            "quality": block.quality
        }
    )
    return {"status": "queued", "block_id": block.block_id}