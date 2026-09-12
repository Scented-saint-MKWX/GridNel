from fastapi import APIRouter, Depends
from .models import get_db

router = APIRouter()

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