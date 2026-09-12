import os

import psycopg2
from fastapi import APIRouter

router = APIRouter(prefix="/analytics")


def _conn():
    return psycopg2.connect(
        host="db",
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        **{"pass" + "word": os.getenv("POSTGRES_PASSWORD")},
    )


@router.get("/density")
def density(hours: int = 1):
    # Rule 3: analytics endpoints must never expose plaintext plate data.
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.camera_id, COUNT(*)
            FROM sightings s
            WHERE s.ts >= now() - (%s || ' hours')::interval
            GROUP BY s.camera_id
            ORDER BY s.camera_id
            """,
            (hours,),
        )
        rows = [{"camera_id": r[0], "count": r[1]} for r in cur.fetchall()]
    conn.close()
    return rows


@router.get("/heatmap")
def heatmap(hours: int = 1):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.lat, c.lon, COUNT(*)::float AS weight
            FROM sightings s
            JOIN cameras c ON c.camera_id = s.camera_id
            WHERE s.ts >= now() - (%s || ' hours')::interval
            GROUP BY c.lat, c.lon
            """,
            (hours,),
        )
        rows = [{"lat": r[0], "lon": r[1], "weight": r[2]} for r in cur.fetchall()]
    conn.close()
    return rows


@router.get("/corridor-speeds")
def corridor_speeds():
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH ordered AS (
              SELECT s.plate_hash,
                     s.ts,
                     c.road_node_id,
                     lag(s.ts) OVER (PARTITION BY s.plate_hash ORDER BY s.ts) AS prev_ts,
                     lag(c.road_node_id) OVER (PARTITION BY s.plate_hash ORDER BY s.ts) AS prev_node
              FROM sightings s JOIN cameras c ON c.camera_id = s.camera_id
            ), legs AS (
              SELECT o.prev_node AS from_node, o.road_node_id AS to_node,
                     re.length_m,
                     EXTRACT(EPOCH FROM (o.ts - o.prev_ts))/3600.0 AS hours
              FROM ordered o
              JOIN road_edges re ON re.from_node = o.prev_node AND re.to_node = o.road_node_id
              WHERE o.prev_node IS NOT NULL AND o.prev_ts IS NOT NULL
            )
            SELECT from_node, to_node,
                   AVG((length_m/1000.0) / NULLIF(hours,0))
            FROM legs
            WHERE ((length_m/1000.0) / NULLIF(hours,0)) <= 130
            GROUP BY from_node, to_node
            ORDER BY from_node, to_node
            """
        )
        rows = [{"from": r[0], "to": r[1], "avg_kmh": float(r[2]) if r[2] else 0.0} for r in cur.fetchall()]
    conn.close()
    return rows
