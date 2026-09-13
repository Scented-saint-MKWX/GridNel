"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
GET /alerts?since=... — both roles, polling only per TEAM.md §4/§11 (no
WebSocket at L1).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from api.deps import require_any_role
from api.models import get_db

router = APIRouter()


@router.get("/alerts")
def get_alerts(since: str = Query(...), user=Depends(require_any_role), conn=Depends(get_db)):
    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        since_dt = datetime.now(timezone.utc)

    cur = conn.cursor()
    cur.execute(
        "SELECT id, type, plate_hash, camera_id, ts, detail FROM alert_events WHERE ts > %s ORDER BY ts ASC",
        (since_dt,),
    )
    rows = cur.fetchall()
    return [
        {
            "id": str(row["id"]),
            "type": row["type"],
            "plate_hash": row["plate_hash"],
            "camera_id": row["camera_id"],
            "ts": row["ts"].isoformat(),
            "detail": row["detail"],
        }
        for row in rows
    ]
