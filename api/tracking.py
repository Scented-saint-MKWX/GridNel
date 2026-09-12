from fastapi import APIRouter, Depends, HTTPException
from typing import List
from .models import get_db
from .schemas import Trackpoint

router = APIRouter()

@router.get("/track/{plate_text}", response_model=List[Trackpoint])
def track_vehicle(plate_text: str, db = Depends(get_db)):
    cur = db.cursor()
    cur.execute("""
        SELECT c.lat, c.lon, s.ts, s.camera_id 
        FROM sightings s
        JOIN cameras c ON s.camera_id = c.camera_id
        WHERE s.plate_text = %s
        ORDER BY s.ts ASC
    """, (plate_text,))
    
    results = cur.fetchall()
    if not results:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    return results