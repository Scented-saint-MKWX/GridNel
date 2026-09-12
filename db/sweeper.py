"""
SentinelGrid — db/sweeper.py
Owner: P3 (Database).

Runs continuously, sleeping RETENTION-window-appropriate intervals, and deletes:
  1. Any `sightings` row older than RETENTION_HOURS (default 24h for the demo).
  2. Any `plates` row left with zero remaining sightings (orphan cleanup).

This is the file the "privacy beat" of the demo points at: run it live, then
query `sightings`/`plates` to show expired rows are actually gone.

Usage:
    python db/sweeper.py            # loop forever, sweep every 5 minutes
    python db/sweeper.py --once     # sweep a single time and exit (useful for demo/testing)
"""

import argparse
import logging
import os
import time

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [sweeper] %(message)s")
log = logging.getLogger("sweeper")

RETENTION_HOURS = int(os.environ.get("RETENTION_HOURS", "24"))
SWEEP_INTERVAL_SECONDS = int(os.environ.get("SWEEP_INTERVAL_SECONDS", "300"))  # 5 minutes

DB_DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        db=os.environ.get("POSTGRES_DB", "sentinelgrid"),
    ),
)

DELETE_EXPIRED_SIGHTINGS_SQL = """
    DELETE FROM sightings
    WHERE ts < now() - (%s || ' hours')::interval
"""

DELETE_ORPHANED_PLATES_SQL = """
    DELETE FROM plates p
    WHERE NOT EXISTS (
        SELECT 1 FROM sightings s WHERE s.plate_hash = p.plate_hash
    )
    AND p.last_seen < now() - (%s || ' hours')::interval
"""


def run_once(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DELETE_EXPIRED_SIGHTINGS_SQL, (RETENTION_HOURS,))
        deleted_sightings = cur.rowcount

        cur.execute(DELETE_ORPHANED_PLATES_SQL, (RETENTION_HOURS,))
        deleted_plates = cur.rowcount

    conn.commit()
    log.info(
        "sweep complete: %d sightings deleted, %d orphaned plates deleted (retention=%dh)",
        deleted_sightings,
        deleted_plates,
        RETENTION_HOURS,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run a single sweep and exit")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    try:
        if args.once:
            run_once(conn)
            return

        log.info("sweeper started (interval=%ds, retention=%dh)", SWEEP_INTERVAL_SECONDS, RETENTION_HOURS)
        while True:
            try:
                run_once(conn)
            except Exception:  # noqa: BLE001 - keep the loop alive; log and retry next interval
                log.exception("sweep failed, will retry next interval")
                conn.rollback()
            time.sleep(SWEEP_INTERVAL_SECONDS)
    finally:
        conn.close()


if __name__ == "__main__":
    main()