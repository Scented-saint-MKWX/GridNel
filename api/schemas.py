from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class Location(BaseModel):
    lat: float
    lon: float

class Resolution(BaseModel):
    fused_as: str
    outcome: str
    vendor_guess: Optional[str] = None
    alt_texts: List[str] = []

class DataBlock(BaseModel):
    block_id: UUID
    camera_id: str
    cam_event_id: str
    ts: datetime
    plate_text: str
    conf: float
    location: Location
    resolution: Resolution
    quality: str

class Trackpoint(BaseModel):
    lat: float
    lon: float
    ts: datetime
    camera_id: str

class AlertOut(BaseModel):
    id: int
    type: str
    plate_text: str
    camera_id: str
    ts: datetime

class BlacklistTargetOut(BaseModel):
    plate_text: str
    reason: str
    added_ts: datetime
    alert_count: int
    last_camera_id: Optional[str] = None
    last_seen_ts: Optional[datetime] = None