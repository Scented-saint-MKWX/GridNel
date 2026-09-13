from fastapi import APIRouter, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
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

def parse_time_interval(interval: Optional[str] = None):
    """Translates interval names to datetime bounds."""
    now = datetime.now(timezone.utc)
    if not interval or interval == "all":
        return None, None
    elif interval == "1h":
        return now - timedelta(hours=1), now
    elif interval == "6h":
        return now - timedelta(hours=6), now
    elif interval == "24h":
        return now - timedelta(hours=24), now
    elif interval == "morning_peak":
        # Simulates peak morning traffic (approx 8:00 - 11:00 AM window)
        return now - timedelta(hours=18), now - timedelta(hours=14)
    elif interval == "evening_peak":
        # Simulates peak evening traffic (approx 5:00 - 8:00 PM window)
        return now - timedelta(hours=7), now - timedelta(hours=3)
    return None, None

@router.get("/analytics/summary")
def get_summary(db = Depends(get_db)):
    cur = db.cursor()
    
    cur.execute("SELECT COUNT(*) as total_sightings FROM sightings")
    sightings = cur.fetchone()["total_sightings"]
    
    cur.execute("SELECT COUNT(*) as total_cameras FROM cameras WHERE status = 'active'")
    cameras = cur.fetchone()["total_cameras"]
    
    cur.execute("SELECT COUNT(*) as active_alerts FROM alert_events")
    alerts = cur.fetchone()["active_alerts"]

    cur.execute("SELECT COUNT(DISTINCT plate_text) as total_vehicles FROM sightings")
    vehicles = cur.fetchone()["total_vehicles"]
    
    return {
        "total_sightings": sightings,
        "active_cameras": cameras,
        "active_alerts": alerts,
        "total_vehicles": vehicles
    }

@router.get("/cameras", response_model=List[CameraOut])
def get_cameras(db = Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT camera_id, lat, lon, zone, road_node_id, status FROM cameras ORDER BY camera_id ASC")
    return cur.fetchall()

@router.get("/analytics/heatmap")
def get_heatmap(
    interval: Optional[str] = Query("all", description="Interval filter: all, 1h, 6h, 24h, morning_peak, evening_peak"),
    db = Depends(get_db)
):
    """
    Returns [lat, lon, normalized_intensity, camera_id, count] for Leaflet heatmaps.
    Supports time interval filtering.
    """
    start_ts, end_ts = parse_time_interval(interval)
    cur = db.cursor()

    query = """
        SELECT c.camera_id, c.lat, c.lon, c.zone, COUNT(s.block_id) as sighting_count
        FROM cameras c
        LEFT JOIN sightings s ON c.camera_id = s.camera_id
    """
    params = []

    if start_ts and end_ts:
        query += " AND s.ts >= %s AND s.ts <= %s "
        params.extend([start_ts, end_ts])
    elif start_ts:
        query += " AND s.ts >= %s "
        params.append(start_ts)

    query += " GROUP BY c.camera_id, c.lat, c.lon, c.zone ORDER BY sighting_count DESC"
    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    if not rows:
        return {"points": [], "max": 1, "interval": interval}

    max_count = max((r["sighting_count"] for r in rows), default=1)
    max_count = max(max_count, 1)

    points = []
    for r in rows:
        count = r["sighting_count"]
        # Normalize intensity between 0.15 and 1.0 for visual heat
        intensity = round(max(0.15, min(1.0, count / max_count)), 3) if count > 0 else 0.05
        points.append({
            "lat": r["lat"],
            "lon": r["lon"],
            "intensity": intensity,
            "count": count,
            "camera_id": r["camera_id"],
            "zone": r["zone"]
        })

    return {
        "interval": interval,
        "max_sighting_count": max_count,
        "total_hotspots": len(points),
        "points": points
    }

@router.get("/analytics/camera/{camera_id}")
def get_camera_traffic(
    camera_id: str,
    interval: Optional[str] = Query("all"),
    db = Depends(get_db)
):
    """
    Detailed traffic analysis for a specific camera node:
    - Total sightings
    - Unique vehicles
    - Congestion rating
    - Recent vehicle plate sightings
    - Hourly volume trend
    """
    start_ts, end_ts = parse_time_interval(interval)
    cur = db.cursor()

    # Camera Info
    cur.execute("SELECT * FROM cameras WHERE camera_id = %s", (camera_id,))
    camera = cur.fetchone()
    if not camera:
        return {"error": f"Camera {camera_id} not found"}

    # Sighting Counts
    count_query = "SELECT COUNT(*) as total, COUNT(DISTINCT plate_text) as unique_v FROM sightings WHERE camera_id = %s"
    params = [camera_id]
    if start_ts and end_ts:
        count_query += " AND ts >= %s AND ts <= %s"
        params.extend([start_ts, end_ts])
    
    cur.execute(count_query, tuple(params))
    stats = cur.fetchone()
    total_sightings = stats["total"]
    unique_vehicles = stats["unique_v"]

    # Congestion Level
    if total_sightings > 80:
        congestion = "CRITICAL"
        status_color = "red"
    elif total_sightings > 40:
        congestion = "HIGH"
        status_color = "amber"
    elif total_sightings > 15:
        congestion = "MODERATE"
        status_color = "blue"
    else:
        congestion = "FLOWING"
        status_color = "emerald"

    # Recent Sightings
    recent_query = """
        SELECT plate_text, ts, conf, quality 
        FROM sightings 
        WHERE camera_id = %s 
        ORDER BY ts DESC 
        LIMIT 10
    """
    cur.execute(recent_query, (camera_id,))
    recent_plates = cur.fetchall()

    return {
        "camera_id": camera_id,
        "zone": camera["zone"],
        "lat": camera["lat"],
        "lon": camera["lon"],
        "interval": interval,
        "total_sightings": total_sightings,
        "unique_vehicles": unique_vehicles,
        "congestion_level": congestion,
        "status_color": status_color,
        "recent_sightings": recent_plates
    }

@router.get("/analytics/density")
def get_zone_density(
    interval: Optional[str] = Query("all"),
    db = Depends(get_db)
):
    """
    Zone-wise aggregate density breakdown across the 6 major hubs.
    """
    start_ts, end_ts = parse_time_interval(interval)
    cur = db.cursor()

    query = """
        SELECT c.zone, COUNT(s.block_id) as total_sightings, COUNT(DISTINCT s.plate_text) as unique_vehicles, COUNT(DISTINCT c.camera_id) as active_cams
        FROM cameras c
        LEFT JOIN sightings s ON c.camera_id = s.camera_id
    """
    params = []
    if start_ts and end_ts:
        query += " AND s.ts >= %s AND s.ts <= %s "
        params.extend([start_ts, end_ts])

    query += " GROUP BY c.zone ORDER BY total_sightings DESC"
    cur.execute(query, tuple(params))
    zones = cur.fetchall()

    total_all = sum(z["total_sightings"] for z in zones) or 1
    for z in zones:
        z["percentage"] = round((z["total_sightings"] / total_all) * 100, 1)

    return {
        "interval": interval,
        "total_grid_sightings": total_all,
        "zones": zones
    }