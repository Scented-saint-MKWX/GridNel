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
    quality: strMa