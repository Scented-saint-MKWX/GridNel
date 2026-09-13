"""
SentinelGrid — api/flusher.py
Pulls real-time data from the Redis stream and writes it to PostgreSQL.
Generates alerts automatically if a license plate matches the blacklist.
"""

import os
import time
import logging
import redis
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [flusher] %(levelname)s: %(message)s")
log = logging.getLogger("flusher")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sentinel")

def get_db_conn():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    return conn

def run_flusher():
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    conn = None
    last_id = "0-0"
    
    log.info("Flusher active. Monitoring sightings:stream on Redis...")
    
    while True:
        try:
            if conn is None or conn.closed:
                conn = get_db_conn()
                cur = conn.cursor()

            # Poll Redis stream; blocks up to 2000ms if empty
            messages = r.xread({"sightings:stream": last_id}, count=50, block=2000)
            if not messages:
                continue

            for _, stream_msgs in messages:
                for msg_id, msg_data in stream_msgs:
                    cam_id = msg_data.get("camera_id", "CAM_01")
                    lat = float(msg_data.get("lat", 28.6139))
                    lon = float(msg_data.get("lon", 77.2090))
                    plate_text = msg_data.get("plate_text", "")
                    block_id = msg_data.get("block_id")
                    ts = msg_data.get("ts")
                    conf = float(msg_data.get("conf", 0.90))
                    outcome = msg_data.get("outcome", "agreement")
                    quality = msg_data.get("quality", "verified")

                    # 1. Ensure camera exists to satisfy foreign key
                    cur.execute("""
                        INSERT INTO cameras (camera_id, lat, lon, zone, road_node_id, status)
                        VALUES (%s, %s, %s, 'Z1', 'N1', 'active')
                        ON CONFLICT (camera_id) DO NOTHING
                    """, (cam_id, lat, lon))

                    # 2. Insert sighting
                    cur.execute("""
                        INSERT INTO sightings (block_id, plate_text, camera_id, ts, conf, outcome, quality)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (block_id) DO NOTHING
                    """, (block_id, plate_text, cam_id, ts, conf, outcome, quality))

                    # 3. Check blacklist
                    cur.execute("SELECT reason FROM blacklist WHERE plate_text = %s", (plate_text,))
                    match = cur.fetchone()
                    if match:
                        reason = match[0]
                        cur.execute("""
                            INSERT INTO alert_events (type, plate_text, camera_id, ts, detail)
                            VALUES ('blacklist_match', %s, %s, %s, %s)
                        """, (
                            plate_text,
                            cam_id,
                            ts,
                            f'{{"reason": "{reason}"}}'
                        ))
                        log.warning(f"🚨 BLACKLIST HIT: Plate {plate_text} at {cam_id}! Reason: {reason}")

                    last_id = msg_id
                    log.info(f"Flushed sighting: {plate_text} at {cam_id}")

        except Exception as e:
            log.error(f"Flusher exception: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            time.sleep(2)

if __name__ == "__main__":
    run_flusher()