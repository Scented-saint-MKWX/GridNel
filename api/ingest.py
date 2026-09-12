import os
import hmac
import redis

from fastapi import HTTPException
from .schemas import DataBlock


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

FOG_API_KEY = os.getenv("FOG_API_KEY")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True
)


def authenticate_fog(api_key: str):
    """
    Verify that the request came from an authorized fog node.
    """

    if not FOG_API_KEY:
        raise RuntimeError("FOG_API_KEY is not configured")

    if not hmac.compare_digest(api_key, FOG_API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid fog API key"
        )


def is_duplicate(block: DataBlock):
    """
    Prevent the same camera + plate hash
    from being accepted more than once within 5 seconds.
    """

    key = f"dedup:{block.camera_id}:{block.plate_hash}"

    created = redis_client.set(
        key,
        "1",
        nx=True,
        ex=5
    )

    return not created


def ingest_block(block: DataBlock, api_key: str):

    # 1. Authenticate fog
    authenticate_fog(api_key)

    # 2. Deduplicate
    if is_duplicate(block):
        return {
            "status": "discarded",
            "reason": "duplicate",
            "block_id": block.block_id
        }

    # 3. Store in Redis Stream
    redis_client.xadd(
        "sightings:stream",
        {
            "block_id": block.block_id,
            "camera_id": block.camera_id,
            "cam_event_id": block.cam_event_id,
            "ts": block.ts,
            "plate_hash": block.plate_hash,
            "plate_text_enc": block.plate_text_enc,
            "conf": str(block.conf),
            "lat": str(block.location.lat),
            "lon": str(block.location.lon),
            "fused_as": block.resolution.fused_as,
            "outcome": block.resolution.outcome,
            "vendor_guess": block.resolution.vendor_guess or "",
            "alt_hashes": ",".join(
                block.resolution.alt_hashes
            ),
            "quality": block.quality
        }
    )

    return {
        "status": "queued",
        "block_id": block.block_id
    }
