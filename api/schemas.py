from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Outcome = Literal["agreement", "engine_preferred", "vendor_preferred", "single_channel", "low_confidence"]
Quality = Literal["full_pipeline", "anpr_fallback", "unverified"]


class Location(BaseModel):
    lat: float
    lon: float


class Resolution(BaseModel):
    fused_as: str
    outcome: Outcome
    vendor_guess: str | None = None
    alt_hashes: list[str] = Field(default_factory=list)


class DataBlock(BaseModel):
    block_id: str
    camera_id: str
    cam_event_id: str
    ts: datetime
    plate_hash: str
    plate_text_enc: str
    conf: float
    location: Location
    resolution: Resolution
    quality: Quality
