from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Optional
from .models import get_db
from .schemas import Trackpoint

router = APIRouter()

VALID_TOKENS = {"sentinel-tactical-token-709", "sentinel-sec-token-99824", "dev-token"}

@router.get("/track/{plate_text}", response_model=List[Trackpoint])
def track_vehicle(
    plate_text: str, 
    authorization: Optional[str] = Header(default=None),
    db = Depends(get_db)
):
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Access Restricted: Law Enforcement Clearance Required to Track Individual Vehicles."
        )
    
    token = authorization.replace("Bearer ", "").strip()
    if token not in VALID_TOKENS:
        raise HTTPException(
            status_code=403, 
            detail="Access Denied: Invalid or expired tactical clearance token."
        )

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