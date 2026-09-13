"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
Pydantic schemas matching TEAM.md §4.1 (data block) and §4.4/§4.4.1 (API shapes)
exactly, field-for-field.
"""
from typing import Literal, Optional

from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lon: float


class Resolution(BaseModel):
    fused_as: str
    outcome: Literal[
        "agreement", "engine_preferred", "vendor_preferred", "single_channel", "low_confidence"
    ]
    vendor_guess: Optional[str] = None
    alt_hashes: list[str] = []


class DataBlock(BaseModel):
    block_id: str
    camera_id: str
    cam_event_id: str
    ts: str
    plate_hash: str
    plate_text_enc: str
    conf: float
    location: Location
    resolution: Resolution
    quality: Literal["full_pipeline", "anpr_fallback", "unverified"]


class LoginRequest(BaseModel):
    username: str
    password: str


class BlacklistRequest(BaseModel):
    plate_text: str
    reason: str
