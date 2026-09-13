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
from dotenv import load_dotenv


# ---------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------

ROOT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

load_dotenv(
    os.path.join(ROOT_DIR, ".env")
)


# ---------------------------------------------------------------
# Logging
# ---------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [fog_sim] %(levelname)s: %(message)s",
)

log = logging.getLogger("fog_sim")


# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------

FOG_API_KEY = os.environ.get("FOG_API_KEY")

API_URL = os.environ.get(
    "API_URL",
    "http://localhost:8000/ingest"
)

CAMERAS_JSON_PATH = os.environ.get(
    "CAMERAS_JSON_PATH",
    os.path.join(ROOT_DIR, "db", "cameras.json")
)

EMIT_INTERVAL_SECONDS = float(
    os.environ.get(
        "EMIT_INTERVAL_SECONDS",
        "2"
    )
)

HTTP_TIMEOUT_SECONDS = float(
    os.environ.get(
        "HTTP_TIMEOUT_SECONDS",
        "5"
    )
)

BLACKLIST_PLATE = os.environ.get(
    "BLACKLIST_PLATE",
    "MH12AB1284"
)

P_BLACKLIST = float(
    os.environ.get(
        "P_BLACKLIST",
        "0.05"
    )
)

P_MISREAD = float(
    os.environ.get(
        "P_MISREAD",
        "0.10"
    )
)

P_LOW_CONF_DROP = float(
    os.environ.get(
        "P_LOW_CONF_DROP",
        "0.05"
    )
)


# ---------------------------------------------------------------
# Normal plates
# ---------------------------------------------------------------

NORMAL_PLATES = [
    "DL8CAF5023",
    "KA05MN1234",
    "TS09EZ7788",
    "MH12AB9911",
    "AP16BT4321",
    "TN10CY6543",
    "PB11AK0192",
]


# ---------------------------------------------------------------
# Load cameras
# ---------------------------------------------------------------

def load_cameras(path: str) -> list[dict]:

    try:
        with open(path, "r") as f:
            cameras = json.load(f)

    except Exception as e:
        sys.exit(
            f"FATAL: Could not load {path}: {e}"
        )

    if not isinstance(cameras, list):
        sys.exit(
            "FATAL: cameras.json must contain a list."
        )

    if len(cameras) == 0:
        sys.exit(
            "FATAL: cameras.json contains no cameras."
        )

    for camera in cameras:

        if "camera_id" not in camera:
            sys.exit(
                f"FATAL: Camera missing camera_id: {camera}"
            )

        if "lat" not in camera:
            sys.exit(
                f"FATAL: Camera missing lat: {camera}"
            )

        if "lon" not in camera:
            sys.exit(
                f"FATAL: Camera missing lon: {camera}"
            )

    log.info(
        "Loaded %d cameras from %s",
        len(cameras),
        path
    )

    return cameras


# ---------------------------------------------------------------
# Generate one-character OCR error
# ---------------------------------------------------------------

def one_char_misread(plate: str) -> str:

    if len(plate) < 2:
        return plate

    index = random.randrange(
        len(plate)
    )

    chars = (
        "ABCDEFGHJKLMNPQRSTUVWXYZ"
        "0123456789"
    )

    original = plate[index]

    possible = [
        c for c in chars
        if c != original
    ]

    replacement = random.choice(
        possible
    )

    return (
        plate[:index]
        + replacement
        + plate[index + 1:]
    )


# ---------------------------------------------------------------
# Generate ONE data block
# ---------------------------------------------------------------

def build_block(camera: dict) -> dict | None:

    # -----------------------------------------------------------
    # Select plate
    # -----------------------------------------------------------

    is_blacklist_hit = (
        random.random() < P_BLACKLIST
    )

    if is_blacklist_hit:

        plate = BLACKLIST_PLATE

    else:

        plate = random.choice(
            NORMAL_PLATES
        )


    # -----------------------------------------------------------
    # Confidence
    # -----------------------------------------------------------

    conf = round(
        random.uniform(
            0.85,
            0.99
        ),
        2
    )


    # -----------------------------------------------------------
    # OCR result
    # -----------------------------------------------------------

    vendor_guess = plate

    outcome = "agreement"

    alt_texts = []


    # -----------------------------------------------------------
    # Simulate OCR misread
    # -----------------------------------------------------------

    if random.random() < P_MISREAD:

        vendor_guess = one_char_misread(
            plate
        )

        outcome = "engine_preferred"

        alt_texts = [
            vendor_guess
        ]


    # -----------------------------------------------------------
    # Simulate low-confidence drop
    # -----------------------------------------------------------

    elif random.random() < P_LOW_CONF_DROP:

        log.info(
            "Dropped low-confidence detection "
            "from %s",
            camera["camera_id"]
        )

        return None


    # -----------------------------------------------------------
    # Create ONE block
    #
    # These fields are compatible with your existing
    # ingestion payload/schema.
    # -----------------------------------------------------------

    block = {

        "block_id": str(
            uuid.uuid4()
        ),

        "camera_id": camera[
            "camera_id"
        ],

        "cam_event_id": (
            "evt_"
            + uuid.uuid4().hex[:8]
        ),

        "ts": datetime.now(
            timezone.utc
        ).isoformat(),

        "plate_text": plate,

        "conf": conf,

        "location": {

            "lat": camera["lat"],

            "lon": camera["lon"]

        },

        "resolution": {

            "fused_as": plate,

            "outcome": outcome,

            "vendor_guess": vendor_guess,

            "alt_texts": alt_texts

        },

        "quality": "unverified"
    }


    # -----------------------------------------------------------
    # Log blacklist hit
    # -----------------------------------------------------------

    if is_blacklist_hit:

        log.warning(
            "BLACKLIST HIT: %s at %s",
            plate,
            camera["camera_id"]
        )


    return block


# ---------------------------------------------------------------
# Send ONE block
# ---------------------------------------------------------------

def send_block(block: dict) -> bool:

    headers = {

        "Content-Type":
            "application/json",

        "Authorization":
            f"Bearer {FOG_API_KEY}"

    }


    try:

        response = requests.post(

            API_URL,

            json=block,

            headers=headers,

            timeout=HTTP_TIMEOUT_SECONDS

        )


        if response.status_code == 200:

            log.info(
                "BLOCK SENT | "
                "camera=%s | "
                "plate=%s | "
                "confidence=%.2f",

                block["camera_id"],

                block["plate_text"],

                block["conf"]
            )

            return True


        log.warning(
            "BLOCK REJECTED | "
            "camera=%s | "
            "status=%s | "
            "%s",

            block["camera_id"],

            response.status_code,

            response.text[:200]
        )

        return False


    except requests.exceptions.RequestException as e:

        log.error(
            "Failed to reach API: %s",
            e
        )

        return False


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main():

    if not FOG_API_KEY:

        sys.exit(
            "FATAL: FOG_API_KEY is not set."
        )


    log.info(
        "Starting fog simulator"
    )

    log.info(
        "API: %s",
        API_URL
    )

    log.info(
        "Camera file: %s",
        CAMERAS_JSON_PATH
    )

    log.info(
        "Interval: %.2f seconds",
        EMIT_INTERVAL_SECONDS
    )


    cameras = load_cameras(
        CAMERAS_JSON_PATH
    )


    # Start from first camera
    camera_index = 0


    try:

        while True:

            # ---------------------------------------------------
            # Select ONE camera
            # ---------------------------------------------------

            camera = cameras[
                camera_index
            ]


            # Move to next camera
            camera_index = (
                camera_index + 1
            ) % len(cameras)


            # ---------------------------------------------------
            # Generate ONE block
            # ---------------------------------------------------

            block = build_block(
                camera
            )


            # ---------------------------------------------------
            # If detection was dropped,
            # wait and move to next camera
            # ---------------------------------------------------

            if block is None:

                time.sleep(
                    EMIT_INTERVAL_SECONDS
                )

                continue


            # ---------------------------------------------------
            # Immediately send ONE block
            # ---------------------------------------------------

            send_block(
                block
            )


            # ---------------------------------------------------
            # Wait before generating next block
            # ---------------------------------------------------

            time.sleep(
                EMIT_INTERVAL_SECONDS
            )


    except KeyboardInterrupt:

        log.info(
            "Fog simulator stopped."
        )


# ---------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------

if __name__ == "__main__":

    main()
