"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
/track + /track/<text>/bridged (real A* over road_edges) + /blacklist +
/debug/hash, per TEAM.md §4/§8. Tracker-only; audit_log written on every
/track* per P5's spec.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.deps import require_role
from api.graph import astar_path
from api.models import get_db, get_redis
from api.schemas import BlacklistRequest
from auth.hashing import hmac_plate

router = APIRouter()

IMPOSSIBLE_SPEED_KMH = 130.0


def _load_cameras(conn) -> dict[str, dict]:
    cur = conn.cursor()
    cur.execute("SELECT camera_id, lat, lon, road_node_id FROM cameras")
    return {row["camera_id"]: row for row in cur.fetchall()}


def _load_edges(conn) -> list[dict]:
    cur = conn.cursor()
    cur.execute("SELECT from_node, to_node, length_m, speed_limit_kmh, typical_speeds FROM road_edges")
    return cur.fetchall()


def _write_audit(conn, who: str, role: str, action: str, target_hash: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_log (who, role, action, target_hash) VALUES (%s, %s, %s, %s)",
        (who, role, action, target_hash),
    )
    conn.commit()


def _fetch_sightings(conn, plate_hash: str) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.camera_id, s.ts, s.conf, s.outcome, s.alt_hashes, c.lat, c.lon
        FROM sightings s JOIN cameras c ON c.camera_id = s.camera_id
        WHERE s.plate_hash = %s
        ORDER BY s.ts ASC
        """,
        (plate_hash,),
    )
    return cur.fetchall()


def _build_observed_segments(rows: list[dict]) -> list[dict]:
    segments = []
    for row in rows:
        segments.append(
            {
                "type": "observed",
                "camera_id": row["camera_id"],
                "ts": row["ts"].isoformat(),
                "lat": row["lat"],
                "lon": row["lon"],
                "outcome": row["outcome"],
                "healed": False,
            }
        )
    return segments


@router.get("/track/{plate_text}")
def track_plain(plate_text: str, user=Depends(require_role("tracker")), conn=Depends(get_db)):
    plate_hash = hmac_plate(plate_text)
    rows = _fetch_sightings(conn, plate_hash)
    _write_audit(conn, user["sub"], user["role"], "track", plate_hash)
    return {"plate": plate_text.upper(), "segments": _build_observed_segments(rows)}


@router.get("/track/{plate_text}/bridged")
def track_bridged(plate_text: str, user=Depends(require_role("tracker")), conn=Depends(get_db)):
    plate_hash = hmac_plate(plate_text)
    rows = _fetch_sightings(conn, plate_hash)
    _write_audit(conn, user["sub"], user["role"], "track_bridged", plate_hash)

    if not rows:
        return {"plate": plate_text.upper(), "segments": []}

    cameras = _load_cameras(conn)
    edges = _load_edges(conn)
    node_coords = {c["road_node_id"]: (c["lat"], c["lon"]) for c in cameras.values()}

    segments: list[dict] = []
    for i, row in enumerate(rows):
        healed = False
        # Impossible-speed check against the previous leg — self-heal via
        # alt_hashes if a variant forms a plausible continuation.
        if i > 0:
            prev = rows[i - 1]
            dt_hours = (row["ts"] - prev["ts"]).total_seconds() / 3600
            if dt_hours > 0:
                dist_km = _haversine(prev["lat"], prev["lon"], row["lat"], row["lon"])
                implied_speed = dist_km / dt_hours
                if implied_speed > IMPOSSIBLE_SPEED_KMH:
                    healed = _try_self_heal(conn, plate_hash, prev, row)

            from_node = cameras[prev["camera_id"]]["road_node_id"]
            to_node = cameras[row["camera_id"]]["road_node_id"]
            if from_node != to_node:
                hour = prev["ts"].hour
                path_nodes = astar_path(edges, node_coords, from_node, to_node, hour)
                if path_nodes and len(path_nodes) > 1:
                    segments.append(
                        {
                            "type": "inferred",
                            "from": prev["camera_id"],
                            "to": row["camera_id"],
                            "ts_start": prev["ts"].isoformat(),
                            "ts_end": row["ts"].isoformat(),
                            "path": [
                                [node_coords[n][1], node_coords[n][0]] for n in path_nodes
                            ],
                            "algorithm": "astar_speed_prior",
                        }
                    )

        segments.append(
            {
                "type": "observed",
                "camera_id": row["camera_id"],
                "ts": row["ts"].isoformat(),
                "lat": row["lat"],
                "lon": row["lon"],
                "outcome": row["outcome"],
                "healed": healed,
            }
        )

    return {"plate": plate_text.upper(), "segments": segments}


def _haversine(lat1, lon1, lat2, lon2) -> float:
    import math

    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(h))


def _try_self_heal(conn, plate_hash: str, prev: dict, row: dict) -> bool:
    """On an impossible-speed leg, check whether either endpoint's alt_hashes
    contains a variant forming a plausible continuation with the other
    endpoint's actual sightings. Simplified per master prompt Phase 6: checks
    variant existence in sightings, not full graph replanning."""
    cur = conn.cursor()
    for alt in (row.get("alt_hashes") or []) + (prev.get("alt_hashes") or []):
        cur.execute(
            "SELECT 1 FROM sightings WHERE plate_hash = %s LIMIT 1", (alt,)
        )
        if cur.fetchone():
            return True
    return False


@router.get("/debug/hash/{text}")
def debug_hash(text: str, user=Depends(require_role("tracker"))):
    return {"plate_text": text.upper(), "plate_hash": hmac_plate(text)}


@router.post("/blacklist")
def add_blacklist(
    body: BlacklistRequest,
    user=Depends(require_role("tracker")),
    conn=Depends(get_db),
):
    plate_hash = hmac_plate(body.plate_text)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO blacklist (plate_hash, reason, added_by)
        VALUES (%s, %s, %s)
        ON CONFLICT (plate_hash) DO UPDATE SET reason = EXCLUDED.reason
        """,
        (plate_hash, body.reason, user["sub"]),
    )
    conn.commit()
    get_redis().sadd("blacklist", plate_hash)
    _write_audit(conn, user["sub"], user["role"], "blacklist_add", plate_hash)
    return {"plate_hash": plate_hash}


@router.delete("/blacklist/{plate_hash}")
def remove_blacklist(
    plate_hash: str,
    user=Depends(require_role("tracker")),
    conn=Depends(get_db),
):
    cur = conn.cursor()
    cur.execute("DELETE FROM blacklist WHERE plate_hash = %s", (plate_hash,))
    conn.commit()
    get_redis().srem("blacklist", plate_hash)
    _write_audit(conn, user["sub"], user["role"], "blacklist_remove", plate_hash)
    return {"status": "removed"}
