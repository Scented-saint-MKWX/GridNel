"""
SentinelGrid — api/flusher.py
Pulls real-time data from the Redis stream and writes it to PostgreSQL.
Generates alerts automatically if a license plate matches the blacklist.
"""

import os
import time
import redis
import psycopg2

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DB_DSN = os.getenv("DATABASE_URL", "postgresql://sentinel_user:12345678@localhost:5432/sentinelgrid")

# Connect to Redis
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def run_flusher():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    last_id = "0-0"
    
    print("Flusher active. Monitoring sightings:stream...")
    
    while True:
        try:
            # Poll the Redis stream; blocks for up to 5000ms if empty
            messages = r.xread({"sightings:stream": last_id}, count=50, block=5000)
            if not messages:
                continue
                
            for _, stream_msgs in messages:
                for msg_id, msg_data in stream_msgs:
                    # 1. Insert sighting directly using the UUID block_id
                    cur.execute("""
                        INSERT INTO sightings (block_id, plate_text, camera_id, ts, conf, outcome, quality)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (block_id) DO NOTHING
                    """, (
                        msg_data['block_id'], 
                        msg_data['plate_text'], 
                        msg_data['camera_id'], 
                        msg_data['ts'], 
                        float(msg_data['conf']), 
                        msg_data['outcome'], 
                        msg_data['quality']
                    ))
                    
                    # 2. Check blacklist and trigger alert for the dashboard
                    cur.execute("SELECT reason FROM blacklist WHERE plate_text = %s", (msg_data['plate_text'],))
                    match = cur.fetchone()
                    if match:
                        cur.execute("""
                            INSERT INTO alert_events (type, plate_text, camera_id, ts, detail)
                            VALUES ('blacklist_match', %s, %s, %s, %s)
                        """, (
                            msg_data['plate_text'], 
                            msg_data['camera_id'], 
                            msg_data['ts'],
                            f'{{"reason": "{match[0]}"}}'
                        ))
                        print(f"ALERT TRIGGERED: Blacklist hit on {msg_data['plate_text']}")

                    last_id = msg_id
                    print(f"Flushed: {msg_data['plate_text']} from {msg_data['camera_id']}")
                    
        except Exception as e:
            print(f"Flusher DB Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    run_flusher()