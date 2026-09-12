"""
SentinelGrid — fog-node/fog_sim.py
Plaintext MVP Mode A mock camera simulator.
"""

import os
import sys
import time
import uuid
import json
import random
import logging
from datetime import datetime, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [fog_sim] %(levelname)s: %(message)s",
)
log = logging.getLogger("fog_sim")

# --- Config ---------------------------------------------------------------
API_URL = os.environ.get("API_URL", "http://localhost:8000/ingest")
FOG_API_KEY = os.environ.get("FOG_API_KEY", "hackathon_secret_key")
CAMERAS_JSON_PATH = os.environ.get("CAMERAS_JSON_PATH", "db/cameras.json")
EMIT_INTERVAL_SECONDS = float(os.environ.get("EMIT_INTERVAL_SECONDS", "2"))
HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "5"))

BLACKLIST_PLATE = os.environ.get("BLACKLIST_PLATE", "MH12AB1284")

P_BLACKLIST = float(os.environ.get("P_BLACKLIST", "0.05"))
P_MISREAD = float(os.environ.get("P_MISREAD", "0.10"))
P_LOW_CONF_DROP = float(os.environ.get("P_LOW_CONF_DROP", "0.05"))

NORMAL_PLATES = [
    "DL8CAF5023",
    "KA05MN1234",
    "TS09EZ7788",
    "MH12AB9911",
    "AP16BT4321",
    "TN10CY6543",
    "PB11AK0192",
]

def load_cameras(path: str) -> list[dict]:
    try:
        with open(path, "r") as f:
            cameras = json.load(f)
    except Exception as e:
        sys.exit(f"FATAL: Could not load {path}. Error: {e}")
    return cameras

def one_char_misread(plate: str) -> str:
    if len(plate) < 2:
        return plate
    idx = random.randrange(len(plate))
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"
    original = plate[idx]
    new_char = random.choice([c for c in chars if c != original])
    return plate[:idx] + new_char + plate[idx + 1:]

def build_block(camera: dict) -> dict | None:
    is_blacklist_hit = random.random() < P_BLACKLIST
    true_plate = BLACKLIST_PLATE if is_blacklist_hit else random.choice(NORMAL_PLATES)

    conf = round(random.uniform(0.85, 0.99), 2)
    vendor_guess = true_plate
    outcome = "agreement"
    alt_texts = []

    if random.random() < P_MISREAD:
        vendor_guess = one_char_misread(true_plate)
        outcome = "engine_preferred"
        alt_texts = [vendor_guess]
    elif random.random() < P_LOW_CONF_DROP:
        log.info("Simulated low-confidence read on %s — dropping.", camera["camera_id"])
        return None

    # Plaintext JSON payload matching schemas.py
    block = {
        "block_id": str(uuid.uuid4()),
        "camera_id": camera["camera_id"],
        "cam_event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "plate_text": true_plate, 
        "conf": conf,
        "location": {"lat": camera["lat"], "lon": camera["lon"]},
        "resolution": {
            "fused_as": true_plate,
            "outcome": outcome,
            "vendor_guess": vendor_guess,
            "alt_texts": alt_texts,
        },
        "quality": "unverified",
    }

    if is_blacklist_hit:
        log.info("Injected BLACKLIST plate %s at %s", true_plate, camera["camera_id"])

    return block

def send_block(block: dict) -> None:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FOG_API_KEY}", 
    }

    try:
        resp = requests.post(API_URL, json=block, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
        if resp.status_code == 200:
            log.info("Sent block for %s (plate=%s) -> 200 OK", block["camera_id"], block["plate_text"])
        else:
            log.warning("Ingest rejected block for %s: %s", block["camera_id"], resp.text[:100])
    except requests.exceptions.RequestException as e:
        log.error("Failed to reach %s: %s", API_URL, e)

def main() -> None:
    log.info("Starting fog_sim — target=%s, interval=%ss", API_URL, EMIT_INTERVAL_SECONDS)
    cameras = load_cameras(CAMERAS_JSON_PATH)
    
    try:
        while True:
            for camera in cameras:
                block = build_block(camera)
                if block:
                    send_block(block)
            time.sleep(EMIT_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log.info("Stopped by user.")

if __name__ == "__main__":
    main()