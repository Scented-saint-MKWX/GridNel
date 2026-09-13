"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
Seeds cameras (from db/cameras.json — frozen shared source, TEAM.md §4.3),
road_edges (small connected graph over the six seeded nodes), and one
blacklisted plate (MH12AB1284, per TEAM.md §8's P3 spec), hashed with the
same auth/hashing.py every producer uses. Run once at container startup.
"""
import json
import os
import sys
import time

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from auth.hashing import encrypt_plate, hmac_plate  # noqa: E402

DB_DSN = (
    f"host={os.environ.get('POSTGRES_HOST', 'postgres')} "
    f"dbname={os.environ['POSTGRES_DB']} "
    f"user={os.environ['POSTGRES_USER']} "
    f"password={os.environ['POSTGRES_PASSWORD']}"
)

BLACKLISTED_PLATE = "MH12AB1284"

# length_m / speed_limit_kmh are illustrative, not surveyed — sized so implied
# transit times are plausible for a same-city hop, per TEAM.md's demo intent.
ROAD_EDGES = [
    ("N1", "N2", 1400, 40),
    ("N2", "N1", 1400, 40),
    ("N2", "N3", 1900, 40),
    ("N3", "N2", 1900, 40),
    ("N1", "N4", 2600, 50),
    ("N4", "N1", 2600, 50),
    ("N1", "N5", 2100, 45),
    ("N5", "N1", 2100, 45),
    ("N1", "N6", 3200, 50),
    ("N6", "N1", 3200, 50),
    ("N4", "N5", 3400, 45),
    ("N5", "N4", 3400, 45),
    ("N5", "N6", 3900, 45),
    ("N6", "N5", 3900, 45),
]

TYPICAL_SPEEDS = {str(h): (25 if 7 <= h <= 10 or 17 <= h <= 20 else 40) for h in range(24)}


def wait_for_db(conn_attempts=30):
    for attempt in range(conn_attempts):
        try:
            return psycopg2.connect(DB_DSN)
        except psycopg2.OperationalError:
            time.sleep(1)
    raise RuntimeError("Postgres never became available")


def main():
    conn = wait_for_db()
    conn.autocommit = True
    cur = conn.cursor()

    cameras_path = os.path.join(os.path.dirname(__file__), "cameras.json")
    with open(cameras_path) as f:
        cameras = json.load(f)

    for cam in cameras:
        cur.execute(
            """
            INSERT INTO cameras (camera_id, lat, lon, zone, road_node_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (camera_id) DO NOTHING
            """,
            (cam["camera_id"], cam["lat"], cam["lon"], cam["zone"], cam["road_node_id"]),
        )

    for from_node, to_node, length_m, speed_limit in ROAD_EDGES:
        cur.execute(
            """
            INSERT INTO road_edges (from_node, to_node, length_m, speed_limit_kmh, typical_speeds)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (from_node, to_node) DO NOTHING
            """,
            (from_node, to_node, length_m, speed_limit, json.dumps(TYPICAL_SPEEDS)),
        )

    plate_hash = hmac_plate(BLACKLISTED_PLATE)
    plate_enc = encrypt_plate(BLACKLISTED_PLATE)
    cur.execute(
        """
        INSERT INTO plates (plate_hash, plate_text_enc, first_seen, last_seen)
        VALUES (%s, %s, now(), now())
        ON CONFLICT (plate_hash) DO NOTHING
        """,
        (plate_hash, plate_enc),
    )
    cur.execute(
        """
        INSERT INTO blacklist (plate_hash, reason, added_by)
        VALUES (%s, %s, %s)
        ON CONFLICT (plate_hash) DO NOTHING
        """,
        (plate_hash, "stolen vehicle report", "seed"),
    )

    print(f"[seed] {len(cameras)} cameras, {len(ROAD_EDGES)} road edges, "
          f"1 blacklisted plate ({BLACKLISTED_PLATE} -> {plate_hash[:12]}...)")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
