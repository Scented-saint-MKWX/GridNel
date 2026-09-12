"""
SentinelGrid — fog-node/buffer.py
The local SQLite safety net. 
If the fog node loses Wi-Fi, it dumps the JSON payloads here.
When the connection returns, it flushes them to the central server.
"""

import sqlite3
import json
import logging
import requests
import os

# Store the database in a local data/ folder inside fog-node
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "buffer.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [buffer] %(levelname)s: %(message)s")
log = logging.getLogger("buffer")

def init_db():
    """Ensure the database and table exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS buffered_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def save_to_buffer(payload: dict) -> None:
    """Save a failed transmission to the local hard drive."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO buffered_blocks (payload) VALUES (?)",
            (json.dumps(payload),)
        )
    log.info("Network down. Buffered block %s to local SQLite storage.", payload.get("block_id"))

def flush_buffer(api_url: str, headers: dict) -> None:
    """Attempt to send all buffered blocks to the central API."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Grab oldest records first
        cursor.execute("SELECT id, payload FROM buffered_blocks ORDER BY created_at ASC")
        rows = cursor.fetchall()

        if not rows:
            return  # Nothing to flush

        log.info("Network restored. Attempting to flush %d buffered blocks...", len(rows))
        
        for row_id, payload_str in rows:
            payload = json.loads(payload_str)
            try:
                # Shoot it to the FastAPI server
                resp = requests.post(api_url, json=payload, headers=headers, timeout=5)
                
                if resp.status_code == 200:
                    # If FastAPI accepted it, delete it from local storage
                    cursor.execute("DELETE FROM buffered_blocks WHERE id = ?", (row_id,))
                    conn.commit()
                    log.info("Successfully flushed block %s", payload.get("block_id"))
                else:
                    log.warning("API rejected buffered block %s: %s", payload.get("block_id"), resp.text)
                    break # Stop flushing to maintain chronological order
                    
            except requests.exceptions.RequestException as e:
                log.error("Network still unreachable during flush: %s", e)
                break # Stop flushing and try again later