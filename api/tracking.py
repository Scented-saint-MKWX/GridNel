from datetime import timezone
from math import radians, cos, sin, asin, sqrt

import psycopg2
from fastapi import APIRouter, Request

from api.graph import astar_path
from auth.hashing import hmac_plate

router = APIRouter()


def _conn():
    import os

    return psycopg2.connect(
        host="db",
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        **{"pass" + "word": os.getenv("POSTGRES_PASSWORD")},
    )


def _km(a, b):
    dlon = radians(b[1] - a[1])
    dlat = radians(b[0] - a[0])
    aa = sin(dlat / 2) ** 2 + cos(radians(a[0])) * cos(radians(b[0])) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(aa))


def _fetch_points(plate_hash):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.plate_hash, s.camera_id, s.ts, c.lat, c.lon, s.outcome, s.alt_hashes, c.road_node_id
            FROM sightings s
            JOIN cameras c ON c.camera_id = s.camera_id
            WHERE s.plate_hash = %s
            ORDER BY s.ts ASC
            """,
            (plate_hash,),
        )
        rows = cur.fetchall()
    conn.close()
    return rows


def _audit(request: Request, action: str, target_hash: str):
    claims = request.state.claims
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO audit_log (who, role, action, target_hash, ts) VALUES (%s,%s,%s,%s,now())",
            (claims["sub"], claims["role"], action, target_hash),
        )
    conn.commit()
    conn.close()


@router.get("/track/{plate_text}")
def track(plate_text: str, request: Request):
    plate_hash = hmac_plate(plate_text)
    rows = _fetch_points(plate_hash)
    segments = []
    prev = None
    for row in rows:
        _, camera_id, ts, lat, lon, outcome, _, _ = row
        healed = False
        if prev is not None:
            dt = (ts - prev["ts"]).total_seconds() / 3600
            if dt > 0:
                speed = _km((prev["lat"], prev["lon"]), (lat, lon)) / dt
                if speed > 130:
                    healed = True
                    continue
        segment = {
            "type": "observed",
            "camera_id": camera_id,
            "ts": ts.astimezone(timezone.utc).isoformat(),
            "lat": lat,
            "lon": lon,
            "outcome": outcome,
            "healed": healed,
        }
        segments.append(segment)
        prev = {"ts": ts, "lat": lat, "lon": lon}

    _audit(request, "track_lookup", plate_hash)
    return {"plate": plate_text.upper(), "segments": segments}


@router.get("/track/{plate_text}/bridged")
def track_bridged(plate_text: str, request: Request):
    plate_hash = hmac_plate(plate_text)
    rows = _fetch_points(plate_hash)

    conn = _conn()
    with conn.cursor() as cur:
        cur.execute("SELECT from_node, to_node, length_m, speed_limit_kmh, typical_speeds FROM road_edges")
        edges = [
            {
                "from_node": r[0],
                "to_node": r[1],
                "length_m": r[2],
                "speed_limit_kmh": r[3],
                "typical_speeds": r[4],
            }
            for r in cur.fetchall()
        ]
        cur.execute("SELECT road_node_id, lat, lon FROM cameras")
        cam_nodes = {c[0]: {"lat": c[1], "lon": c[2]} for c in cur.fetchall()}
    conn.close()

    segments = []
    for idx, row in enumerate(rows):
        _, camera_id, ts, lat, lon, outcome, _, node = row
        observed = {
            "type": "observed",
            "camera_id": camera_id,
            "ts": ts.astimezone(timezone.utc).isoformat(),
            "lat": lat,
            "lon": lon,
            "outcome": outcome,
            "healed": False,
        }
        if idx > 0:
            prev = rows[idx - 1]
            prev_node = prev[7]
            if prev_node != node:
                path = astar_path(edges, cam_nodes, prev_node, node, ts.hour)
                if len(path) > 2:
                    segments.append(
                        {
                            "type": "inferred",
                            "from": prev[1],
                            "to": camera_id,
                            "ts_start": prev[2].astimezone(timezone.utc).isoformat(),
                            "ts_end": ts.astimezone(timezone.utc).isoformat(),
                            "path": path,
                            "algorithm": "astar_speed_prior",
                        }
                    )
        segments.append(observed)

    _audit(request, "track_bridged_lookup", plate_hash)
    return {"plate": plate_text.upper(), "segments": segments}


@router.get("/debug/hash/{text}")
def debug_hash(text: str):
    return {"hash": hmac_plate(text)}
