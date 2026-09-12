from fastapi import APIRouter, Depends
from typing import List
from .models import get_db
from .schemas import AlertOut

router = APIRouter()

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