"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
Redis stream -> batch Postgres insert, per TEAM.md §4/§8: consumer group,
batch 200 rows or 3s, upsert plates.first_seen/last_seen, XACK after commit,
restart-safe. Runs as its own container (see docker-compose.yml).
"""
import json
import logging
import time

from api.models import get_conn, get_redis

logging.basicConfig(level=logging.INFO, format="[flusher] %(message)s")
log = logging.getLogger(__name__)

STREAM = "sightings:stream"
GROUP = "flusher-group"
CONSUMER = "flusher-1"
BATCH_SIZE = 200
BATCH_TIMEOUT_MS = 3000


def ensure_group(r):
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise


def sync_blacklist_to_redis(r):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT plate_hash FROM blacklist")
        rows = cur.fetchall()
    if rows:
        r.sadd("blacklist", *[row["plate_hash"] for row in rows])


def flush_batch(entries: list[tuple[str, dict]]):
    with get_conn() as conn:
        cur = conn.cursor()
        for _id, fields in entries:
            plate_hash = fields["plate_hash"]
            cur.execute(
                """
                INSERT INTO plates (plate_hash, plate_text_enc, first_seen, last_seen)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (plate_hash) DO UPDATE SET
                    last_seen = GREATEST(plates.last_seen, EXCLUDED.last_seen),
                    plate_text_enc = EXCLUDED.plate_text_enc
                """,
                (plate_hash, fields["plate_text_enc"], fields["ts"], fields["ts"]),
            )
            cur.execute(
                """
                INSERT INTO sightings (plate_hash, camera_id, ts, conf, outcome, alt_hashes, quality)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    plate_hash,
                    fields["camera_id"],
                    fields["ts"],
                    float(fields["conf"]),
                    fields["outcome"],
                    json.loads(fields.get("alt_hashes", "[]")),
                    fields["quality"],
                ),
            )
        conn.commit()


def flush_alerts(entries: list[tuple[str, dict]]):
    with get_conn() as conn:
        cur = conn.cursor()
        for _id, fields in entries:
            cur.execute(
                """
                INSERT INTO alert_events (type, plate_hash, camera_id, ts, detail)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    fields["type"],
                    fields["plate_hash"],
                    fields["camera_id"],
                    fields["ts"],
                    fields.get("detail", "{}"),
                ),
            )
        conn.commit()


def run():
    r = get_redis()
    ensure_group(r)
    ensure_group_for(r, "alerts:stream")
    sync_blacklist_to_redis(r)
    log.info("flusher started, consuming %s and alerts:stream", STREAM)

    while True:
        resp = r.xreadgroup(
            GROUP, CONSUMER, {STREAM: ">"}, count=BATCH_SIZE, block=BATCH_TIMEOUT_MS
        )
        if resp:
            for _stream_name, entries in resp:
                try:
                    flush_batch(entries)
                    r.xack(STREAM, GROUP, *[eid for eid, _ in entries])
                except Exception:
                    log.exception("batch flush failed, will retry on next read")

        alert_resp = r.xreadgroup(
            "alerts-group", CONSUMER, {"alerts:stream": ">"}, count=BATCH_SIZE, block=100
        )
        if alert_resp:
            for _stream_name, entries in alert_resp:
                try:
                    flush_alerts(entries)
                    r.xack("alerts:stream", "alerts-group", *[eid for eid, _ in entries])
                except Exception:
                    log.exception("alert flush failed, will retry on next read")


def ensure_group_for(r, stream: str):
    try:
        r.xgroup_create(stream, "alerts-group", id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise


if __name__ == "__main__":
    while True:
        try:
            run()
        except Exception:
            log.exception("flusher crashed, restarting in 2s")
            time.sleep(2)
