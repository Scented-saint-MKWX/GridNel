"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a."""
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import redis

DB_DSN = (
    f"host={os.environ.get('POSTGRES_HOST', 'postgres')} "
    f"dbname={os.environ['POSTGRES_DB']} "
    f"user={os.environ['POSTGRES_USER']} "
    f"password={os.environ['POSTGRES_PASSWORD']}"
)

_redis_client: redis.Redis | None = None


@contextmanager
def get_conn():
    conn = psycopg2.connect(DB_DSN, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    return _redis_client


def get_db():
    with get_conn() as conn:
        yield conn
