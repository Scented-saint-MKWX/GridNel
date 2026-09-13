from fastapi import APIRouter, Depends
from typing import List
from .models import get_db
from .schemas import AlertOut, BlacklistTargetOut

router = APIRouter()

@router.get("/alerts/targets", response_model=List[BlacklistTargetOut])
def get_blacklist_targets(db = Depends(get_db)):
    """Returns all blacklisted plates with threat reasons and total detection counts."""
    cur = db.cursor()
    cur.execute("""
        SELECT 
            b.plate_text,
            b.reason,
            b.added_ts,
            COALESCE(COUNT(a.id), 0) AS alert_count,
            MAX(a.camera_id) AS last_camera_id,
            MAX(a.ts) AS last_seen_ts
        FROM blacklist b
        LEFT JOIN alert_events a ON b.plate_text = a.plate_text
        GROUP BY b.plate_text, b.reason, b.added_ts
        ORDER BY alert_count DESC, last_seen_ts DESC NULLS LAST
    """)
    return cur.fetchall()

@router.get("/alerts", response_model=List[AlertOut])
def get_recent_alerts(limit: int = 10, db = Depends(get_db)):
    cur = db.cursor()
    cur.execute("""
        SELECT id, type, plate_text, camera_id, ts 
        FROM alert_events 
        ORDER BY ts DESC 
        LIMIT %s
    """, (limit,))
    
    return cur.fetchall()