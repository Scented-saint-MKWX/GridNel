import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_DSN = os.getenv("DATABASE_URL", "postgresql://sentinel_user:12345678@localhost:5432/sentinelgrid")

def get_db():
    conn = psycopg2.connect(DB_DSN, cursor_factory=RealDictCursor,row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()