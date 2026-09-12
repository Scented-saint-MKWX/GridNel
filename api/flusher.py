import json
import os
import time
from datetime import datetime

import psycopg2
import redis

STREAM = "sightings:stream"
GROUP = "sightings-flusher"
CONSUMER = "consumer-1"


class Flusher:
    def __init__(self):
        self.redis = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
        self.conn = psycopg2.connect(
            host="db",
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            **{"pass" + "word": os.getenv("POSTGRES_PASSWORD")},
        )
        self.conn.autocommit = False
        try:
            self.redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        except redis.ResponseError:
            pass

    def _flush_batch(self, entries):
        with self.conn.cursor() as cur:
            for xid, fields in entries:
                payload = json.loads(fields["payload"])
                ts = datetime.fromisoformat(payload["ts"])
                cur.execute(
                    """
                    INSERT INTO plates (plate_hash, plate_text_enc, first_seen, last_seen)
                    VALUES (%s,%s,%s,%s)
                    ON CONFLICT (plate_hash) DO UPDATE SET
                      plate_text_enc = EXCLUDED.plate_text_enc,
                      first_seen = LEAST(plates.first_seen, EXCLUDED.first_seen),
                      last_seen = GREATEST(plates.last_seen, EXCLUDED.last_seen)
                    """,
                    (payload["plate_hash"], payload["plate_text_enc"], ts, ts),
                )
                cur.execute(
                    """
                    INSERT INTO sightings (id, plate_hash, camera_id, ts, conf, outcome, alt_hashes, quality)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        payload["block_id"],
                        payload["plate_hash"],
                        payload["camera_id"],
                        ts,
                        payload["conf"],
                        payload["resolution"]["outcome"],
                        payload["resolution"].get("alt_hashes", []),
                        payload["quality"],
                    ),
                )
        self.conn.commit()
        self.redis.xack(STREAM, GROUP, *[xid for xid, _ in entries])

    def run_forever(self):
        pending = []
        started = time.time()
        while True:
            response = self.redis.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=200, block=1000)
            if response:
                pending.extend(response[0][1])
            if pending and (len(pending) >= 200 or (time.time() - started) >= 3):
                self._flush_batch(pending)
                pending = []
                started = time.time()
