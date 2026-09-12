import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import requests

from auth.hashing import encrypt_plate, hmac_plate
from pipeline import pipeline

API_BASE = os.getenv("API_BASE_URL", "http://api:8000")
FOG_API_KEY = os.getenv("FOG_API_KEY", "")
MODE = os.getenv("FOG_MODE", "A").upper()

CAMERAS = json.loads(Path("/app/db/cameras.json").read_text())
KNOWN = ["MH12AB1284", "DL05CD4321", "UP16EF7654", "HR26GH5555"]


def one_char_misread(text: str) -> str:
    idx = random.randrange(len(text))
    c = text[idx]
    repl = "8" if c != "8" else "B"
    return text[:idx] + repl + text[idx + 1 :]


def fabricate_block(camera, plate, vendor_guess, outcome="agreement", conf=0.93):
    alt = []
    if vendor_guess and vendor_guess != plate:
        alt = [hmac_plate(vendor_guess)]
    return {
        "block_id": str(uuid4()),
        "camera_id": camera["camera_id"],
        "cam_event_id": f"evt_{uuid4().hex[:6]}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "plate_hash": hmac_plate(plate),
        "plate_text_enc": encrypt_plate(plate),
        "conf": conf,
        "location": {"lat": camera["lat"], "lon": camera["lon"]},
        "resolution": {
            "fused_as": plate,
            "outcome": outcome,
            "vendor_guess": vendor_guess,
            "alt_hashes": alt,
        },
        "quality": "anpr_fallback" if MODE == "A" else "full_pipeline",
    }


def stream_events():
    while True:
        cam = random.choice(CAMERAS)
        plate = "MH12AB1284" if random.random() < 0.05 else random.choice(KNOWN)
        vendor_guess = plate
        outcome = "agreement"
        conf = 0.94

        if random.random() < 0.10:
            vendor_guess = one_char_misread(plate)
            outcome = "engine_preferred"
        if random.random() < 0.05:
            conf = 0.70
            outcome = "low_confidence"

        if MODE == "B":
            img = np.zeros((80, 220, 3), dtype=np.uint8)
            result = pipeline(img, vendor_guess, cam["camera_id"], cam["lat"], cam["lon"], f"evt_{uuid4().hex[:6]}")
            if result is None:
                time.sleep(0.8)
                continue
            block, _ = result
        else:
            if conf < 0.85:
                time.sleep(0.8)
                continue
            block = fabricate_block(cam, plate, vendor_guess, outcome=outcome, conf=conf)

        # Rule 2: only data block leaves fog node.
        resp = requests.post(
            f"{API_BASE}/ingest",
            json=block,
            headers={"x-api-key": FOG_API_KEY},
            timeout=5,
        )
        print(f"ingest {block['camera_id']} {block['resolution']['fused_as']} -> {resp.status_code}")
        time.sleep(0.8)


if __name__ == "__main__":
    stream_events()
