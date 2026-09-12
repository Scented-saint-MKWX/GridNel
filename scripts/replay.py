"""Record and replay a fog_sim run against /ingest.

TEAM.md §7/§13 + FRONTEND_BLUEPRINT.md §6: "the demo runs on replay, not
live mode." Two subcommands:

  record  - listens for blocks (piped in via stdin, one JSON block per line,
            e.g. from a modified fog_sim run, or read from an existing
            recording to re-time it) and writes them to a recording file with
            each block's delay (seconds since the previous block) captured.
  replay  - re-POSTs a recorded run's blocks to /ingest in identical order,
            with identical relative timing, every time it's invoked. No
            randomness at replay time — all randomness (which plate, which
            camera, which outcome) happened once, at record time.

Recording format: JSON lines, each `{"delay_s": <float>, "block": {...}}`.
delay_s is the time to sleep *before* posting this block, relative to the
previous one (0 for the first line) — this is what "identical timing" means.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
API_URL = os.environ.get("API_URL", "http://localhost:8000")
FOG_API_KEY = os.environ.get("FOG_API_KEY")

DEFAULT_RECORDING = REPO_ROOT / "scripts" / "recordings" / "demo_run.jsonl"


def record(input_stream, out_path: Path) -> None:
    """Read one JSON block per line from input_stream and write a timed
    recording. Blocks arrive live (e.g. piped from a fog_sim variant that
    prints each block as JSON instead of just POSTing it) — this captures
    the actual demo run once, including whatever a blacklist hit or bridged
    gap looked like live, so replay can reproduce that exact run forever."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    last_ts = None
    count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for line in input_stream:
            line = line.strip()
            if not line:
                continue
            block = json.loads(line)
            now = time.monotonic()
            delay_s = 0.0 if last_ts is None else now - last_ts
            last_ts = now
            f.write(json.dumps({"delay_s": round(delay_s, 3), "block": block}) + "\n")
            f.flush()
            count += 1
            print(f"recorded block {count} ({block.get('camera_id', '?')}), delay {delay_s:.2f}s")
    print(f"recording complete: {count} blocks -> {out_path}")


def load_recording(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} does not exist. Record a run first: replay.py record")
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise SystemExit(f"{path} is empty — nothing to replay.")
    return lines


def replay(path: Path, speed: float) -> None:
    """Re-drives a recorded run through /ingest in identical order and
    timing (scaled by --speed). Deterministic: no randomness happens here —
    every block, every delay, comes verbatim from the recording."""
    entries = load_recording(path)
    headers = {"Content-Type": "application/json"}
    if FOG_API_KEY:
        headers["X-Fog-Api-Key"] = FOG_API_KEY

    print(f"replaying {len(entries)} blocks from {path} at {speed}x speed -> {API_URL}/ingest")
    for i, entry in enumerate(entries, start=1):
        delay_s = entry["delay_s"] / speed
        if delay_s > 0:
            time.sleep(delay_s)
        block = entry["block"]
        try:
            resp = requests.post(f"{API_URL}/ingest", json=block, headers=headers, timeout=5)
            print(f"[{i}/{len(entries)}] POST /ingest [{block.get('camera_id', '?')}] -> {resp.status_code}")
        except requests.RequestException as exc:
            print(f"[{i}/{len(entries)}] POST /ingest failed: {exc}")
    print("replay complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record/replay a fog_sim run against /ingest")
    sub = parser.add_subparsers(dest="command", required=True)

    record_parser = sub.add_parser("record", help="record blocks from stdin (one JSON block per line)")
    record_parser.add_argument("--out", type=Path, default=DEFAULT_RECORDING)

    replay_parser = sub.add_parser("replay", help="replay a recorded run")
    replay_parser.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_RECORDING)
    replay_parser.add_argument("--speed", type=float, default=1.0, help="playback speed multiplier")

    args = parser.parse_args()
    if args.command == "record":
        record(sys.stdin, args.out)
    else:
        replay(args.in_path, args.speed)
