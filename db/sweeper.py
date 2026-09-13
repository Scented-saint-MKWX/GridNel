"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
TTL sweeper: deletes expired sightings and orphaned plates every 5 minutes,
per TEAM.md §7/§8. Retention window from RETENTION_HOURS (default 24).
"""
import logging
import os
import time

import psycopg2

logging.basicConfig(level=logging.INFO, format="[sweeper] %(message)s")
log = logging.getLogger(__name__)

DB_DSN = (
    f"host={os.environ.get('POSTGRES_HOST', 'postgres')} "
    f"dbname={os.environ['POSTGRES_DB']} "
    f"user={os.environ['POSTGRES_USER']} "
    f"password={os.environ['POSTGRES_PASSWORD']}"
)
RETENTION_HOURS = float(os.environ.get("RETENTION_HOURS", "24"))
INTERVAL_SECONDS = 5 * 60


def wait_for_db(attempts=30):
    for _ in range(attempts):
        try:
            return psycopg2.connect(DB_DSN)
        except psycopg2.OperationalError:
            time.sleep(1)
    raise RuntimeError("Postgres never became available")


def sweep_once(conn):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM sightings WHERE ts < now() - (%s || ' hours')::interval",
        (RETENTION_HOURS,),
    )
    deleted_sightings = cur.rowcount
    cur.execute(
        """
        DELETE FROM plates
        WHERE plate_hash NOT IN (SELECT DISTINCT plate_hash FROM sightings)
          AND plate_hash NOT IN (SELECT plate_hash FROM blacklist)
          AND last_seen < now() - (%s || ' hours')::interval
        """,
        (RETENTION_HOURS,),
    )
    deleted_plates = cur.rowcount
    conn.commit()
    log.info("swept %s sightings, %s orphaned plates", deleted_sightings, deleted_plates)


def main():
    conn = wait_for_db()
    while True:
        try:
            sweep_once(conn)
        except Exception:
            log.exception("sweep failed, retrying next cycle")
            conn.rollback()
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
