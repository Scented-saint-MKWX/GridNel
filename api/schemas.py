from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class Resolution(BaseModel):
    fused_as: str
    outcome: str
    vendor_guess: Optional[str] = None
    alt_hashes: List[str] = []

class Location(BaseModel):
    lat: float
    lon: float

class DataBlock(BaseModel):
    block_id: str
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