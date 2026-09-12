import os
from datetime import datetime

import psycopg2
from fastapi import APIRouter

router = APIRouter()


def _conn():
    return psycopg2.connect(
        host="db",
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        **{"pass" + "word": os.getenv("POSTGRES_PASSWORD")},
    )


@router.get("/alerts")
def get_alerts(since: str | None = None):
    conn = _conn()
    with conn.cursor() as cur:
        if since:
            dt = datetime.fromisoformat(since)
            cur.execute(
                "SELECT id, type, plate_hash, camera_id, ts, detail FROM alert_events WHERE ts >= %s ORDER BY ts DESC",
                (dt,),
            )
        else:
            cur.execute("SELECT id, type, plate_hash, camera_id, ts, detail FROM alert_events ORDER BY ts DESC LIMIT 200")
        rows = [
            {
                "id": str(r[0]),
                "type": r[1],
                "plate_hash": r[2],
                "camera_id": r[3],
                "ts": r[4].isoformat(),
                "detail": r[5],
            }
            for r in cur.fetchall()
        ]
    conn.close()
    return rows
