from fastapi import APIRouter, Depends
from typing import List
from pydantic import BaseModel
from .models import get_db

router = APIRouter()

class CameraOut(BaseModel):
    camera_id: str
    lat: float
    lon: float
    zone: str
    road_node_id: str
    status: str

@router.get("/analytics/summary")
def get_summary(db = Depends(get_db)):
    cur = db.cursor()
    
    cur.execute("SELECT COUNT(*) as total_sightings FROM sightings")
    sightings = cur.fetchone()["total_sightings"]
    
    cur.execute("SELECT COUNT(*) as total_cameras FROM cameras WHERE status = 'active'")
    cameras = cur.fetchone()["total_cameras"]
    
    cur.execute("SELECT COUNT(*) as active_alerts FROM alert_events")
    alerts = cur.fetchone()["active_alerts"]
    
    return {
        "total_sightings": sightings,
        "active_cameras": cameras,
        "active_alerts": alerts
    }

@router.get("/cameras", response_model=List[CameraOut])
def get_cameras(db = Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT camera_id, lat, lon, zone, road_node_id, status FROM cameras ORDER BY camera_id ASC")
    return cur.fetchall()