import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sentinel")

def get_db():
    conn = psycopg2.connect(DB_DSN, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()