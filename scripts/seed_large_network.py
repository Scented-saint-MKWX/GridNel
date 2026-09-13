"""
SentinelGrid — scripts/seed_large_network.py
Expands network to 300 ANPR cameras and simulates sightings for 2,000 vehicles.
Inserts cameras, road edges, blacklist entries, and realistic sightings into PostgreSQL.
"""

import os
import json
import random
import uuid
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import execute_batch

DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sentinel")

ZONES = ["Z1_Central", "Z2_North", "Z3_South", "Z4_East", "Z5_West", "Z6_Airport"]
STATE_CODES = ["DL", "MH", "HR", "UP", "KA", "TS", "PB", "RJ"]
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"

def generate_300_cameras() -> list[dict]:
    # Center around Central Delhi: 28.6139, 77.2090
    cameras = []
    
    # 6 major hubs with sub-clusters
    hubs = [
        {"name": "Z1_Central", "lat": 28.6139, "lon": 77.2090, "count": 60},
        {"name": "Z2_North",   "lat": 28.6700, "lon": 77.2150, "count": 50},
        {"name": "Z3_South",   "lat": 28.5400, "lon": 77.2200, "count": 50},
        {"name": "Z4_East",    "lat": 28.6250, "lon": 77.2900, "count": 45},
        {"name": "Z5_West",    "lat": 28.6350, "lon": 77.1200, "count": 50},
        {"name": "Z6_Airport", "lat": 28.5600, "lon": 77.1000, "count": 45},
    ]

    cam_idx = 1
    for hub in hubs:
        for _ in range(hub["count"]):
            cam_id = f"CAM_{cam_idx:03d}"
            # Random offset around hub (approx 1-5 km)
            lat = round(hub["lat"] + random.gauss(0, 0.018), 5)
            lon = round(hub["lon"] + random.gauss(0, 0.018), 5)
            cameras.append({
                "camera_id": cam_id,
                "lat": lat,
                "lon": lon,
                "zone": hub["name"],
                "road_node_id": f"N_{cam_idx}"
            })
            cam_idx += 1

    return cameras

def generate_2000_plates() -> list[str]:
    plates = ["MH12AB1284"] # Preserve primary blacklist target
    used = set(plates)

    random.seed(42)
    while len(plates) < 2000:
        state = random.choice(STATE_CODES)
        rto = f"{random.randint(1, 99):02d}"
        series_len = random.choice([1, 2])
        series = "".join(random.choice(LETTERS) for _ in range(series_len))
        num = f"{random.randint(1000, 9999):04d}"
        plate = f"{state}{rto}{series}{num}"
        
        if plate not in used:
            used.add(plate)
            plates.append(plate)

    return plates

def seed_database():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Insert 300 Cameras
    cameras = generate_300_cameras()
    print(f"Seeding {len(cameras)} cameras...")
    
    # Save to db/cameras.json as well
    cameras_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "cameras.json")
    with open(cameras_json_path, "w") as f:
        json.dump(cameras, f, indent=2)
    print(f"Saved to {cameras_json_path}")

    cam_tuples = [(c["camera_id"], c["lat"], c["lon"], c["zone"], c["road_node_id"]) for c in cameras]
    execute_batch(cur, """
        INSERT INTO cameras (camera_id, lat, lon, zone, road_node_id, status)
        VALUES (%s, %s, %s, %s, %s, 'active')
        ON CONFLICT (camera_id) DO UPDATE 
        SET lat = EXCLUDED.lat, lon = EXCLUDED.lon, zone = EXCLUDED.zone;
    """, cam_tuples)

    # 2. Blacklist Seed
    blacklist_plates = [
        ("MH12AB1284", "Reported stolen in Sector 4"),
        ("DL01AB9999", "Suspicious vehicle warrant"),
        ("HR26DQ0007", "Hit and run alert"),
        ("UP16BT1111", "Vehicle with forged plates"),
        ("TS09EZ0001", "High priority surveillance target")
    ]
    for bp, reason in blacklist_plates:
        cur.execute("""
            INSERT INTO blacklist (plate_text, reason, added_by, added_ts)
            VALUES (%s, %s, 'system_seed', now())
            ON CONFLICT (plate_text) DO NOTHING;
        """, (bp, reason))

    # 3. Generate 2000 vehicles & Sightings across last 24 hours
    plates = generate_2000_plates()
    print(f"Generated {len(plates)} vehicles. Simulating realistic traffic flow across 24h...")

    now = datetime.now(timezone.utc)
    sightings = []
    alert_events = []

    # Cluster high traffic in Central (Z1) and North/South during morning/evening rush hours
    for plate in plates:
        is_bl = any(plate == b[0] for b in blacklist_plates)
        # Vehicles make 2 to 12 sightings (trips across corridor)
        hops = random.randint(3, 14) if is_bl else random.randint(2, 8)
        
        # Pick a zone anchor
        hub_idx = random.randint(0, len(ZONES) - 1)
        zone_cameras = [c for c in cameras if c["zone"] == ZONES[hub_idx]]
        if not zone_cameras:
            zone_cameras = cameras[:50]

        # Sighting start time distributed in last 24h with morning (8-11) and evening (17-20) weighting
        hour_offset = random.choices(
            population=list(range(24)),
            weights=[2, 1, 1, 1, 2, 4, 8, 14, 18, 16, 12, 10, 9, 10, 11, 13, 17, 20, 19, 15, 11, 8, 5, 3],
            k=1
        )[0]
        trip_start = now - timedelta(hours=hour_offset, minutes=random.randint(0, 59))
        
        current_cam = random.choice(zone_cameras)
        current_time = trip_start

        for hop in range(hops):
            block_id = str(uuid.uuid4())
            conf = round(random.uniform(0.85, 0.99), 2)
            quality = "verified" if conf > 0.90 else "unverified"
            
            sightings.append((
                block_id,
                plate,
                current_cam["camera_id"],
                current_time.isoformat(),
                conf,
                "agreement",
                quality
            ))

            if is_bl:
                alert_events.append((
                    "blacklist_match",
                    plate,
                    current_cam["camera_id"],
                    current_time.isoformat(),
                    '{"reason": "Seeded surveillance target"}'
                ))

            # Next hop to a nearby camera
            nearby = sorted(cameras, key=lambda c: (c["lat"] - current_cam["lat"])**2 + (c["lon"] - current_cam["lon"])**2)[1:8]
            current_cam = random.choice(nearby)
            current_time += timedelta(minutes=random.randint(2, 12))

    print(f"Bulk inserting {len(sightings)} sightings into PostgreSQL...")
    execute_batch(cur, """
        INSERT INTO sightings (block_id, plate_text, camera_id, ts, conf, outcome, quality)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (block_id) DO NOTHING;
    """, sightings, page_size=2000)

    if alert_events:
        print(f"Inserting {len(alert_events)} blacklist alert events...")
        execute_batch(cur, """
            INSERT INTO alert_events (type, plate_text, camera_id, ts, detail)
            VALUES (%s, %s, %s, %s, %s);
        """, alert_events, page_size=1000)

    # Verification counts
    cur.execute("SELECT COUNT(*) FROM cameras")
    total_cams = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT plate_text) FROM sightings")
    unique_vehicles = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sightings")
    total_sightings = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM alert_events")
    total_alerts = cur.fetchone()[0]

    print("=" * 60)
    print("NETWORK SEED COMPLETE:")
    print(f"  Cameras in Grid:     {total_cams} (Target: 300)")
    print(f"  Unique Vehicles:     {unique_vehicles} (Target: 2000)")
    print(f"  Total Sightings:     {total_sightings}")
    print(f"  Blacklist Alerts:    {total_alerts}")
    print("=" * 60)

    conn.close()

if __name__ == "__main__":
    seed_database()

