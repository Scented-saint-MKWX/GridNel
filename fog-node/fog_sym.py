"""
fog_sim.py — Mode A mock camera / fog node simulator.

Emits fabricated data blocks matching the FROZEN contract in TEAM.md
section 4.1, and POSTs them to the central API's /ingest endpoint.

No real image processing happens here — this is pure fabrication to
unblock the API/DB/frontend teams before enhance.py/ocr.py/fusion.py
exist (per TEAM.md Section 7, hour 0-3).


"""

import os
import sys
import time
import uuid
import json
import random
import logging
from datetime import datetime, timezone, timedelta

import requests

# --- Make the shared auth/ module importable -------------------------------
# auth/hashing.py must be mounted into this container (Docker volume) so the
# fog node and the API use the EXACT same HMAC/AES logic ("one import, one
# behavior" — TEAM.md section 4.2). We do NOT fall back to home-rolled crypto
# if this import fails — that would silently produce hashes/ciphertext the
# real API can never match, which is worse than crashing loudly.
sys.path.insert(0, "/app")
try:
    from auth.hashing import hmac_plate, encrypt_plate
except ImportError as e:
    sys.exit(
        "FATAL: could not import auth.hashing (hmac_plate/encrypt_plate).\n"
        "Check that auth/ is volume-mounted into this container and that "
        "hashing.py exists and exports these two functions.\n"
        f"Original error: {e}"
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [fog_sim] %(levelname)s: %(message)s",
)
log = logging.getLogger("fog_sim")

# --- Config (env-driven so docker-compose.yml controls behavior) -----------
API_URL = os.environ.get("API_URL", "http://api:8000/ingest")
FOG_API_KEY = os.environ.get("FOG_API_KEY")
CAMERAS_JSON_PATH = os.environ.get("CAMERAS_JSON_PATH", "/app/db/cameras.json")
EMIT_INTERVAL_SECONDS = float(os.environ.get("EMIT_INTERVAL_SECONDS", "2"))
HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "5"))

# The one plate seeded as blacklisted in db/seed.sql (TEAM.md section 8, P3).
BLACKLIST_PLATE = os.environ.get("BLACKLIST_PLATE", "MH12AB1284")

# Injection probabilities per TEAM.md Section 7 (hour 16-26 demo realism).
# Set these to 0 via env if you want clean, predictable blocks while
# testing /ingest for the first time.
P_BLACKLIST = float(os.environ.get("P_BLACKLIST", "0.05"))
P_MISREAD = float(os.environ.get("P_MISREAD", "0.10"))
P_LOW_CONF_DROP = float(os.environ.get("P_LOW_CONF_DROP", "0.05"))

IST = timezone(timedelta(hours=5, minutes=30))

# A small pool of non-blacklisted test plates.
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
    """Load the frozen camera list — never hardcode cameras (TEAM.md 4.3)."""
    try:
        with open(path, "r") as f:
            cameras = json.load(f)
    except FileNotFoundError:
        sys.exit(f"FATAL: cameras.json not found at {path}. Mount db/ into this container.")
    except json.JSONDecodeError as e:
        sys.exit(f"FATAL: cameras.json is not valid JSON: {e}")

    if not cameras:
        sys.exit("FATAL: cameras.json loaded but is empty.")

    required_keys = {"camera_id", "lat", "lon"}
    for cam in cameras:
        missing = required_keys - cam.keys()
        if missing:
            sys.exit(f"FATAL: camera {cam.get('camera_id', '?')} missing keys: {missing}")

    return cameras


def one_char_misread(plate: str) -> str:
    """Flip one alphanumeric character to simulate a vendor OCR misread."""
    if len(plate) < 2:
        return plate
    idx = random.randrange(len(plate))
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"  # no I/O to avoid look-alikes
    original = plate[idx]
    new_char = random.choice([c for c in chars if c != original])
    return plate[:idx] + new_char + plate[idx + 1:]


def build_block(camera: dict) -> dict | None:
    """
    Build one fabricated data block for a given camera, applying the
    Section 6 fusion outcomes probabilistically since fusion.py doesn't
    exist yet. Returns None if this "read" should be dropped (rule 4/5:
    a garbage block is worse than no block).
    """
    is_blacklist_hit = random.random() < P_BLACKLIST
    true_plate = BLACKLIST_PLATE if is_blacklist_hit else random.choice(NORMAL_PLATES)

    conf = round(random.uniform(0.85, 0.99), 2)
    vendor_guess = true_plate
    outcome = "agreement"
    alt_hashes = []

    if random.random() < P_MISREAD:
        vendor_guess = one_char_misread(true_plate)
        # Engine (our fused result) wins; vendor's differing guess goes to alt_hashes.
        outcome = "engine_preferred"
        alt_hashes = [hmac_plate(vendor_guess)]
    elif random.random() < P_LOW_CONF_DROP:
        # Simulate rule 4: differ by >=2 chars, best conf below threshold -> DROP.
        log.info("Simulated low-confidence read on %s — dropping (no block sent).", camera["camera_id"])
        return None

    plate_hash = hmac_plate(true_plate)
    plate_text_enc = encrypt_plate(true_plate)

    block = {
        "block_id": str(uuid.uuid4()),
        "camera_id": camera["camera_id"],
        "cam_event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "ts": datetime.now(IST).isoformat(),
        "plate_hash": plate_hash,
        "plate_text_enc": plate_text_enc,
        "conf": conf,
        "location": {"lat": camera["lat"], "lon": camera["lon"]},
        "resolution": {
            "fused_as": true_plate,
            "outcome": outcome,
            "vendor_guess": vendor_guess,
            "alt_hashes": alt_hashes,
        },
        
        "quality": "unverified",
    }

    if is_blacklist_hit:
        log.info("Injected BLACKLIST plate %s at %s", true_plate, camera["camera_id"])

    return block


def send_block(block: dict) -> None:
    if not FOG_API_KEY:
        sys.exit("FATAL: FOG_API_KEY env var is not set.")

    headers = {
        "Content-Type": "application/json",
        # ⚠️ confirm exact header name with P4/P5 — see module docstring.
        "X-Fog-Api-Key": FOG_API_KEY,
    }

    try:
        resp = requests.post(API_URL, json=block, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
        if resp.status_code == 200:
            log.info(
                "Sent block for %s (plate=%s, outcome=%s) -> 200",
                block["camera_id"], block["resolution"]["fused_as"], block["resolution"]["outcome"],
            )
        else:
            log.warning(
                "Ingest rejected block for %s: %s %s",
                block["camera_id"], resp.status_code, resp.text[:300],
            )
    except requests.exceptions.RequestException as e:
        log.error("Failed to reach %s: %s", API_URL, e)


def main() -> None:
    log.info("Starting fog_sim (mode A) — target=%s, interval=%ss", API_URL, EMIT_INTERVAL_SECONDS)
    cameras = load_cameras(CAMERAS_JSON_PATH)
    log.info("Loaded %d cameras from %s", len(cameras), CAMERAS_JSON_PATH)

    try:
        while True:
            for camera in cameras:
                block = build_block(camera)
                if block is not None:
                    send_block(block)
                time.sleep(EMIT_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log.info("Stopped by user.")


if __name__ == "__main__":
    main()