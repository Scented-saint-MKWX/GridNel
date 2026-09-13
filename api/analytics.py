"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
GET /cameras + the five /analytics/* endpoints, shapes exactly as TEAM.md
§4.4.1 (Nawfal's handoff) — analyst role, aggregated only, never plaintext.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, Query

from api.deps import require_any_role, require_role
from api.models import get_db

router = APIRouter()


@router.get("/cameras")
def list_cameras(conn=Depends(get_db)):
    # Not role-gated — frontend's lib/cameras.ts fetches this unauthenticated
    # from a Next.js server route (hooks/useCameras.ts: "this data isn't
    # behind the backend's auth"). Camera positions carry no PII.
    cur = conn.cursor()
    cur.execute("SELECT camera_id, lat, lon, road_node_id FROM cameras")
    rows = cur.fetchall()
    return {
        "cameras": [
            {
                "camera_id": r["camera_id"],
                "latitude": r["lat"],
                "longitude": r["lon"],
                "road_id": r["road_node_id"],
            }
            for r in rows
        ]
    }


def _camera_pair_speed(conn, from_camera: str, to_camera: str, hours: int) -> tuple[int, float, float]:
    """vehicle_count, avg_speed_kmh, avg_travel_time_sec for consecutive
    sightings of the same plate crossing this camera pair, excluding
    >130 km/h legs as misreads (TEAM.md §8 P4 spec)."""
    cur = conn.cursor()
    cur.execute(
        """
        WITH ordered AS (
            SELECT plate_hash, camera_id, ts,
                   LAG(camera_id) OVER (PARTITION BY plate_hash ORDER BY ts) AS prev_camera,
                   LAG(ts) OVER (PARTITION BY plate_hash ORDER BY ts) AS prev_ts
            FROM sightings
            WHERE ts > now() - (%s || ' hours')::interval
        )
        SELECT prev_ts, ts FROM ordered
        WHERE prev_camera = %s AND camera_id = %s
        """,
        (hours, from_camera, to_camera),
    )
    rows = cur.fetchall()

    cur.execute(
        "SELECT length_m FROM road_edges re JOIN cameras cf ON cf.road_node_id = re.from_node "
        "JOIN cameras ct ON ct.road_node_id = re.to_node "
        "WHERE cf.camera_id = %s AND ct.camera_id = %s LIMIT 1",
        (from_camera, to_camera),
    )
    edge = cur.fetchone()
    length_m = edge["length_m"] if edge else 2000.0

    speeds = []
    times = []
    for row in rows:
        dt_sec = (row["ts"] - row["prev_ts"]).total_seconds()
        if dt_sec <= 0:
            continue
        speed_kmh = (length_m / 1000) / (dt_sec / 3600)
        if speed_kmh > 130:
            continue
        speeds.append(speed_kmh)
        times.append(dt_sec)

    count = len(speeds)
    avg_speed = sum(speeds) / count if count else 0.0
    avg_time = sum(times) / count if count else 0.0
    return count, avg_speed, avg_time


def _congestion(avg_speed_kmh: float, speed_limit_kmh: float) -> str:
    if speed_limit_kmh <= 0:
        return "LOW"
    ratio = avg_speed_kmh / speed_limit_kmh
    if ratio < 0.5:
        return "HIGH"
    if ratio < 0.8:
        return "MEDIUM"
    return "LOW"


def _camera_pairs(conn) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cf.camera_id AS from_camera, ct.camera_id AS to_camera,
               re.from_node AS from_road, re.to_node AS to_road, re.speed_limit_kmh,
               re.geometry
        FROM road_edges re
        JOIN cameras cf ON cf.road_node_id = re.from_node
        JOIN cameras ct ON ct.road_node_id = re.to_node
        """
    )
    return cur.fetchall()


@router.get("/analytics/summary")
def analytics_summary(hours: int = Query(1), user=Depends(require_role("analyst")), conn=Depends(get_db)):
    pairs = _camera_pairs(conn)
    total_vehicles = 0
    total_transitions = 0
    all_speeds = []
    all_times = []
    congested = 0

    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(DISTINCT plate_hash) AS c FROM sightings WHERE ts > now() - (%s || ' hours')::interval",
        (hours,),
    )
    total_vehicles = cur.fetchone()["c"]

    for pair in pairs:
        count, avg_speed, avg_time = _camera_pair_speed(conn, pair["from_camera"], pair["to_camera"], hours)
        if count == 0:
            continue
        total_transitions += count
        all_speeds.extend([avg_speed] * count)
        all_times.append(avg_time)
        if _congestion(avg_speed, pair["speed_limit_kmh"]) == "HIGH":
            congested += 1

    avg_speed_kmh = sum(all_speeds) / len(all_speeds) if all_speeds else 0.0
    sorted_speeds = sorted(all_speeds)
    median_speed_kmh = (
        sorted_speeds[len(sorted_speeds) // 2] if sorted_speeds else 0.0
    )
    avg_travel_time_sec = sum(all_times) / len(all_times) if all_times else 0.0

    return {
        "vehicles_analyzed": total_vehicles,
        "transitions_analyzed": total_transitions,
        "average_speed_kmh": round(avg_speed_kmh, 1),
        "median_speed_kmh": round(median_speed_kmh, 1),
        "average_travel_time_sec": round(avg_travel_time_sec),
        "congested_segments": congested,
        "total_segments": len(pairs),
    }


@router.get("/analytics/segments")
def analytics_segments(hours: int = Query(1), user=Depends(require_role("analyst")), conn=Depends(get_db)):
    pairs = _camera_pairs(conn)
    segments = []
    for pair in pairs:
        count, avg_speed, avg_time = _camera_pair_speed(conn, pair["from_camera"], pair["to_camera"], hours)
        segments.append(
            {
                "from_camera": pair["from_camera"],
                "to_camera": pair["to_camera"],
                "from_road": pair["from_road"],
                "to_road": pair["to_road"],
                "vehicle_count": count,
                "average_speed_kmh": round(avg_speed, 1),
                "average_travel_time_sec": round(avg_time),
                "congestion": _congestion(avg_speed, pair["speed_limit_kmh"]),
                # Real OSM edge vertices [[lon,lat],...], DECISIONS.md #8 —
                # added so the frontend can draw the actual street path
                # instead of a straight camera-to-camera line.
                "geometry": pair["geometry"] or [],
            }
        )
    return {"segments": segments}


@router.get("/analytics/heatmap")
def analytics_heatmap(hours: int = Query(1), user=Depends(require_role("analyst")), conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.camera_id, c.lat, c.lon, COUNT(s.id) AS vehicle_count
        FROM cameras c
        LEFT JOIN sightings s ON s.camera_id = c.camera_id AND s.ts > now() - (%s || ' hours')::interval
        GROUP BY c.camera_id, c.lat, c.lon
        """,
        (hours,),
    )
    rows = cur.fetchall()
    points = []
    for row in rows:
        cur.execute(
            """
            SELECT AVG(speed) AS avg_speed FROM (
                SELECT (2000.0/1000) / (EXTRACT(EPOCH FROM (s.ts - lag_ts)) / 3600) AS speed
                FROM (
                    SELECT ts, LAG(ts) OVER (PARTITION BY plate_hash ORDER BY ts) AS lag_ts
                    FROM sightings WHERE camera_id = %s AND ts > now() - (%s || ' hours')::interval
                ) s(ts, lag_ts)
                WHERE lag_ts IS NOT NULL
            ) sub WHERE speed <= 130
            """,
            (row["camera_id"], hours),
        )
        speed_row = cur.fetchone()
        points.append(
            {
                "camera_id": row["camera_id"],
                "latitude": row["lat"],
                "longitude": row["lon"],
                "vehicle_count": row["vehicle_count"],
                "average_speed_kmh": round(speed_row["avg_speed"] or 0.0, 1),
            }
        )
    return {"points": points}


def _road_edge_geometry_map(conn) -> dict[tuple[str, str], list]:
    cur = conn.cursor()
    cur.execute("SELECT from_node, to_node, geometry FROM road_edges")
    return {(r["from_node"], r["to_node"]): (r["geometry"] or []) for r in cur.fetchall()}


def _path_geometry(road_sequence: list[str], edge_geom: dict[tuple[str, str], list]) -> list[list[float]]:
    """Concatenates each hop's real edge geometry into one continuous path
    for a road_id sequence, DECISIONS.md #8 — real vertices end-to-end,
    not a straight line between the sequence's endpoints. Falls back to []
    (frontend keeps its existing straight-line rendering) for any hop with
    no direct road_edges row, e.g. non-adjacent road_ids in the sequence."""
    geometry: list[list[float]] = []
    for a, b in zip(road_sequence[:-1], road_sequence[1:]):
        seg = edge_geom.get((a, b))
        if not seg:
            return []
        if geometry and seg[0] == geometry[-1]:
            geometry.extend(seg[1:])
        else:
            geometry.extend(seg)
    return geometry


@router.get("/analytics/od")
def analytics_od(hours: int = Query(1), user=Depends(require_role("analyst")), conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute(
        """
        WITH ordered AS (
            SELECT plate_hash, camera_id, ts,
                   FIRST_VALUE(camera_id) OVER (PARTITION BY plate_hash ORDER BY ts) AS origin_camera,
                   LAST_VALUE(camera_id) OVER (
                       PARTITION BY plate_hash ORDER BY ts
                       ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                   ) AS dest_camera
            FROM sightings
            WHERE ts > now() - (%s || ' hours')::interval
        )
        SELECT DISTINCT plate_hash, origin_camera, dest_camera FROM ordered
        WHERE origin_camera != dest_camera
        """,
        (hours,),
    )
    rows = cur.fetchall()

    cur.execute("SELECT camera_id, road_node_id FROM cameras")
    road_by_camera = {r["camera_id"]: r["road_node_id"] for r in cur.fetchall()}

    flow_counts: dict[tuple[str, str], int] = {}
    for row in rows:
        origin_road = road_by_camera.get(row["origin_camera"])
        dest_road = road_by_camera.get(row["dest_camera"])
        if not origin_road or not dest_road:
            continue
        key = (origin_road, dest_road)
        flow_counts[key] = flow_counts.get(key, 0) + 1

    edge_geom = _road_edge_geometry_map(conn)
    flows = [
        {
            "origin": origin,
            "destination": dest,
            "vehicle_count": count,
            # Real shortest-path geometry between origin/destination road_ids
            # where a direct road_edges hop exists, DECISIONS.md #8. Empty
            # when origin/destination aren't directly adjacent in road_edges
            # — frontend falls back to its existing straight-line draw.
            "geometry": _path_geometry([origin, dest], edge_geom),
        }
        for (origin, dest), count in flow_counts.items()
    ]
    return {"flows": flows}


@router.get("/analytics/routes")
def analytics_routes(hours: int = Query(1), user=Depends(require_role("analyst")), conn=Depends(get_db)):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT plate_hash, array_agg(camera_id ORDER BY ts) AS camera_sequence
        FROM sightings
        WHERE ts > now() - (%s || ' hours')::interval
        GROUP BY plate_hash
        HAVING COUNT(*) > 1
        """,
        (hours,),
    )
    rows = cur.fetchall()

    cur.execute("SELECT camera_id, road_node_id FROM cameras")
    road_by_camera = {r["camera_id"]: r["road_node_id"] for r in cur.fetchall()}

    route_counts: dict[tuple[str, ...], int] = {}
    for row in rows:
        road_sequence = tuple(
            road_by_camera[c] for c in row["camera_sequence"] if c in road_by_camera
        )
        # Collapse consecutive duplicates (same road, multiple cameras).
        collapsed = tuple(r for i, r in enumerate(road_sequence) if i == 0 or r != road_sequence[i - 1])
        if len(collapsed) > 1:
            route_counts[collapsed] = route_counts.get(collapsed, 0) + 1

    edge_geom = _road_edge_geometry_map(conn)
    routes = []
    for i, (road_sequence, count) in enumerate(
        sorted(route_counts.items(), key=lambda kv: -kv[1])
    ):
        routes.append(
            {
                "route_id": f"route_{i + 1}",
                "road_sequence": list(road_sequence),
                "vehicle_count": count,
                "average_speed_kmh": 0.0,
                "average_travel_time_sec": 0,
                # Full concatenated real path vertices across every hop,
                # DECISIONS.md #8. Empty if any hop lacks a direct
                # road_edges row (frontend falls back to straight lines).
                "geometry": _path_geometry(list(road_sequence), edge_geom),
            }
        )
    return {"routes": routes}
