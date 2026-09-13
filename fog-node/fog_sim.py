"""Mock fog node — mode A (instant mock) and mode B (real pipeline).

Mode A emits fabricated data blocks matching TEAM.md §4.1 exactly and POSTs
them to /ingest. No OCR, no real camera crops — exists purely to give P4 a
live producer before P1's real pipeline exists (TEAM.md §7 hour 0-3).

Mode B drives P1's real fog-node/pipeline.py (enhance -> OCR -> fusion) over
a directory of image crops, per TEAM.md §7 hour 16+. Mirrors the auth.hashing
fallback pattern in DECISIONS.md §2: if pipeline.py isn't landed yet or still
raises NotImplementedError, mode B prints a loud warning and falls back to
mode A's fabricated blocks rather than crashing — never blocks the demo on a
teammate's file not being ready yet.

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
IMAGES_DIR = REPO_ROOT / "fog-node" / "images"

# Default injection probabilities per TEAM.md §7 hour 16-26 sim injections /
# FRONTEND_BLUEPRINT.md §6: p~0.05 blacklisted plate, p~0.10 one-char vendor
# misread (exercises engine_preferred fusion display), p~0.05 low-confidence
# drop. Override via CLI flags for demo tuning or rehearsal determinism.
DEFAULT_BLACKLIST_P = 0.05
DEFAULT_MISREAD_P = 0.10
DEFAULT_DROP_P = 0.05

# Mode B: drive P1's real pipeline.py (fog-node/pipeline.py, a sibling of this
# file). "fog-node" has a hyphen so it isn't an importable package name;
# pipeline.py is imported directly since this file's own directory is on
# sys.path when run as a script.
#
# NOT CONFIRMED WITH P1: TEAM.md §8 states the done-shape as
# "pipeline.py(image, vendor_guess) -> (plate, conf, alt_hashes)" but doesn't
# name the callable. Assuming `run_pipeline` below as a placeholder guess,
# not a contract we're allowed to invent per CLAUDE.md's "when stuck" rule —
# flag to P1 and confirm the real name/signature before mode B is relied on
# for the actual demo; until then this import will simply fail and mode B
# falls back to mode A's fabricated blocks (loud warning, not a crash).
_USING_REAL_PIPELINE = False
try:
    from pipeline import run_pipeline  # type: ignore[import]

    _USING_REAL_PIPELINE = True
except Exception:  # noqa: BLE001 - pipeline.py may not exist yet, or is a stub
    pass

def _generate_sample_plates(count: int) -> list[str]:
    """Proportionally larger simulated plate pool for the scaled ~300-camera
    seed (Master Prompt v10 Phase 3) — more distinct vehicles in circulation
    so sightings/transitions volume looks like real city traffic rather than
    5 plates looping through 300 cameras. Deterministic (fixed seed) so
    demo/replay runs stay reproducible across invocations."""
    state_codes = ["MH", "DL", "KA", "RJ", "UP", "TN", "GJ", "WB", "AP", "PB"]
    rng = random.Random(7)
    plates = ["MH12AB1284"]  # seeded blacklisted plate per TEAM.md §8 (P3 spec) — always first
    seen = {plates[0]}
    while len(plates) < count:
        state = rng.choice(state_codes)
        district = rng.randint(1, 20)
        letters = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(2))
        digits = rng.randint(1000, 9999)
        plate = f"{state}{district:02d}{letters}{digits}"
        if plate not in seen:
            seen.add(plate)
            plates.append(plate)
    return plates


SAMPLE_PLATES = _generate_sample_plates(60)

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


def emit_block(block: dict, camera_id: str, headers: dict, *, record_mode: bool) -> None:
    """POST to /ingest normally, or print the block as a JSON line on stdout
    for scripts/replay.py's `record` subcommand to capture — see that file's
    docstring for the recording format. record_mode never also POSTs: a
    recording session and a live-ingest session are separate invocations."""
    if record_mode:
        print(json.dumps(block), flush=True)
        return
    try:
        resp = requests.post(f"{API_URL}/ingest", json=block, headers=headers, timeout=5)
        print(f"POST /ingest [{camera_id}] -> {resp.status_code}", file=sys.stderr)
    except requests.RequestException as exc:
        print(f"POST /ingest failed: {exc}", file=sys.stderr)


def run_mode_a(
    interval: float, blacklist_p: float, misread_p: float, drop_p: float, *, record_mode: bool = False
) -> None:
    cameras = load_cameras()
    headers = {"Content-Type": "application/json"}
    if FOG_API_KEY:
        headers["X-Fog-Api-Key"] = FOG_API_KEY

    print(f"fog_sim mode A: {len(cameras)} cameras, posting to {API_URL}/ingest", file=sys.stderr)
    while True:
        camera = random.choice(cameras)
        block = make_block(camera, blacklist_p=blacklist_p, misread_p=misread_p, drop_p=drop_p)
        if block is None:
            time.sleep(interval)
            continue
        emit_block(block, camera["camera_id"], headers, record_mode=record_mode)
        time.sleep(interval)


def run_mode_b(
    interval: float, blacklist_p: float, misread_p: float, drop_p: float, *, record_mode: bool = False
) -> None:
    """Drive real crops through P1's pipeline.py. Falls back to mode A's
    fabricated blocks (loud warning, not a crash) if pipeline.py isn't landed
    yet, per DECISIONS.md §2's fallback pattern."""
    if not _USING_REAL_PIPELINE:
        print(
            "WARNING: fog-node/pipeline.py not available (or import failed) — "
            "mode B cannot run real crops through enhance->OCR->fusion. "
            "Falling back to mode A's fabricated blocks. Flag to P1 if this "
            "persists past TEAM.md's hour-16 mode-B target.",
            file=sys.stderr,
        )
        run_mode_a(interval, blacklist_p, misread_p, drop_p, record_mode=record_mode)
        return

    if not IMAGES_DIR.exists() or not any(IMAGES_DIR.iterdir()):
        raise SystemExit(
            f"{IMAGES_DIR} does not exist or is empty. Mode B needs real crops "
            "to drive through pipeline.py — see P1's validation dataset "
            "(TEAM.md §8, gitignored dev-only folder)."
        )

    cameras = load_cameras()
    headers = {"Content-Type": "application/json"}
    if FOG_API_KEY:
        headers["X-Fog-Api-Key"] = FOG_API_KEY
    crop_paths = sorted(p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))

    print(
        f"fog_sim mode B: {len(cameras)} cameras, {len(crop_paths)} crops, posting to {API_URL}/ingest",
        file=sys.stderr,
    )
    while True:
        camera = random.choice(cameras)
        crop_path = random.choice(crop_paths)
        vendor_guess = SAMPLE_PLATES[0] if random.random() < blacklist_p else random.choice(SAMPLE_PLATES[1:])

        plate, conf, alt_hashes = run_pipeline(str(crop_path), vendor_guess)  # type: ignore[name-defined]
        if random.random() < drop_p:
            time.sleep(interval)
            continue

        block = {
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
                "outcome": "engine_preferred" if plate != vendor_guess else "agreement",
                "vendor_guess": vendor_guess,
                "alt_hashes": alt_hashes,
            },
            "quality": "full_pipeline",
        }
        emit_block(block, camera["camera_id"], headers, record_mode=record_mode)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelGrid fog node mock")
    parser.add_argument("--mode", choices=["a", "b"], default="a", help="a = fabricated blocks, b = real pipeline.py on fog-node/images/ crops")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between events")
    parser.add_argument("--blacklist-p", type=float, default=DEFAULT_BLACKLIST_P, help="probability of emitting the blacklisted plate")
    parser.add_argument("--misread-p", type=float, default=DEFAULT_MISREAD_P, help="probability of a one-char vendor misread")
    parser.add_argument("--drop-p", type=float, default=DEFAULT_DROP_P, help="probability of a low-confidence drop")
    parser.add_argument(
        "--record",
        action="store_true",
        help="print each block as a JSON line on stdout instead of POSTing — "
        "pipe into `scripts/replay.py record` to capture a run for the demo",
    )
    args = parser.parse_args()
    if args.mode == "a":
        run_mode_a(args.interval, args.blacklist_p, args.misread_p, args.drop_p, record_mode=args.record)
    else:
        run_mode_b(args.interval, args.blacklist_p, args.misread_p, args.drop_p, record_mode=args.record)
