"""Mock fog node — mode A (instant mock, hour 0-3 unblock per TEAM.md).

Emits fabricated data blocks matching TEAM.md §4.1 exactly and POSTs them to
/ingest. No OCR, no real camera crops — this exists purely to give P4 a live
producer before P1's real pipeline exists. Mode B (real pipeline.py) is a
later addition per TEAM.md §7 hour 16+; this file only implements mode A.

Camera positions are read from db/cameras.json at runtime, never hardcoded
here — see TEAM.md §4.3 and CLAUDE.md's hard rule on this.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMERAS_PATH = REPO_ROOT / "db" / "cameras.json"
sys.path.insert(0, str(REPO_ROOT))

# auth/hashing.py is P5's file (auth/ is not our lane). Import the real thing
# when it exists; fall back to an obviously-fake placeholder otherwise so
# fog_sim can still unblock P4's /ingest work today. No manual swap needed —
# once P5 lands real hashing.py this import just starts succeeding.
_USING_REAL_HASHING = False
try:
    from auth.hashing import encrypt_plate, hmac_plate  # type: ignore[import]

    _USING_REAL_HASHING = True
except (ImportError, NotImplementedError):

    def hmac_plate(text: str) -> str:
        return f"unhashed::{text}"

    def encrypt_plate(text: str) -> str:
        return base64.b64encode(f"PLACEHOLDER::{text}".encode()).decode()

    print(
        "WARNING: auth.hashing not available — fog_sim emitting PLACEHOLDER "
        "hash/enc values; blacklist matching and tracking search will not "
        "work until P5's auth/hashing.py lands.",
        file=sys.stderr,
    )

API_URL = os.environ.get("API_URL", "http://localhost:8000")
FOG_API_KEY = os.environ.get("FOG_API_KEY")

SAMPLE_PLATES = [
    "MH12AB1284",  # seeded blacklisted plate per TEAM.md §8 (P3 spec)
    "DL3CAX9981",
    "KA05MN2210",
    "RJ14GT5567",
    "UP16BZ3321",
]

OUTCOMES = ["agreement", "engine_preferred", "vendor_preferred", "single_channel"]


def load_cameras() -> list[dict]:
    if not CAMERAS_PATH.exists():
        raise SystemExit(
            f"{CAMERAS_PATH} does not exist. fog_sim.py reads camera positions "
            "from the shared seed — nobody hardcodes them (TEAM.md §4.3). "
            "Ask P3 to populate it before running the simulator."
        )
    raw = CAMERAS_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        raise SystemExit(
            f"{CAMERAS_PATH} is empty. fog_sim.py cannot fabricate camera "
            "positions — ask P3 to populate the frozen seed."
        )
    cameras = json.loads(raw)
    if not cameras:
        raise SystemExit(f"{CAMERAS_PATH} parsed but contains no cameras.")
    return cameras


def make_block(camera: dict, *, blacklist_p: float, misread_p: float, drop_p: float) -> dict | None:
    plate = SAMPLE_PLATES[0] if random.random() < blacklist_p else random.choice(SAMPLE_PLATES[1:])
    conf = round(random.uniform(0.85, 0.99), 2)
    outcome = random.choice(OUTCOMES)

    vendor_guess = plate
    alt_hashes: list[str] = []
    if outcome in ("engine_preferred", "vendor_preferred") and random.random() < misread_p:
        # one-char misread injection — exercises the fusion display beat,
        # TEAM.md §7 hour 16-26 sim injections. alt_hashes carries the HMAC
        # of the *rejected* variant, per TEAM.md §4.1.
        chars = list(plate)
        idx = random.randrange(len(chars))
        chars[idx] = random.choice("0123456789")
        vendor_guess = "".join(chars)
        alt_hashes = [hmac_plate(vendor_guess)]

    if outcome == "low_confidence" or random.random() < drop_p:
        return None  # a garbage block is worse than no block — TEAM.md §6

    return {
        "block_id": str(uuid.uuid4()),
        "camera_id": camera["camera_id"],
        "cam_event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "plate_hash": hmac_plate(plate),
        "plate_text_enc": encrypt_plate(plate),
        "conf": conf,
        "location": {"lat": camera["lat"], "lon": camera["lon"]},
        "resolution": {
            "fused_as": plate,
            "outcome": outcome,
            "vendor_guess": vendor_guess,
            "alt_hashes": alt_hashes,
        },
        "quality": "unverified",
    }


def run(interval: float, blacklist_p: float, misread_p: float, drop_p: float) -> None:
    cameras = load_cameras()
    headers = {"Content-Type": "application/json"}
    if FOG_API_KEY:
        headers["X-Fog-Api-Key"] = FOG_API_KEY

    print(f"fog_sim mode A: {len(cameras)} cameras, posting to {API_URL}/ingest")
    while True:
        camera = random.choice(cameras)
        block = make_block(camera, blacklist_p=blacklist_p, misread_p=misread_p, drop_p=drop_p)
        if block is None:
            time.sleep(interval)
            continue
        try:
            resp = requests.post(f"{API_URL}/ingest", json=block, headers=headers, timeout=5)
            print(f"POST /ingest [{camera['camera_id']}] -> {resp.status_code}")
        except requests.RequestException as exc:
            print(f"POST /ingest failed: {exc}")
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelGrid fog node mock (mode A)")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between events")
    parser.add_argument("--blacklist-p", type=float, default=0.0, help="probability of emitting the blacklisted plate")
    parser.add_argument("--misread-p", type=float, default=0.0, help="probability of a one-char vendor misread")
    parser.add_argument("--drop-p", type=float, default=0.0, help="probability of a low-confidence drop")
    args = parser.parse_args()
    run(args.interval, args.blacklist_p, args.misread_p, args.drop_p)
