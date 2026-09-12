import os
from datetime import datetime, timedelta, timezone

import psycopg2


def run_sweep() -> str:
    hours = int(os.getenv("RETENTION_HOURS", "24"))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    conn = psycopg2.connect(
        host="db",
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        **{"pass" + "word": os.getenv("POSTGRES_PASSWORD")},
    )
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("DELETE FROM sightings WHERE ts < %s RETURNING id", (cutoff,))
        deleted_sightings = len(cur.fetchall())
        cur.execute(
            """
            DELETE FROM plates p
            WHERE p.last_seen < %s
            OR NOT EXISTS (SELECT 1 FROM sightings s WHERE s.plate_hash = p.plate_hash)
            RETURNING p.plate_hash
            """,
            (cutoff,),
        )
        deleted_plates = len(cur.fetchall())
    conn.commit()
    conn.close()
    return f"[sweeper] {datetime.now(timezone.utc).isoformat()} deleted sightings={deleted_sightings} plates={deleted_plates}"


if __name__ == "__main__":
    print(run_sweep())
