#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import requests


def record(base_url: str, api_key: str, out_file: Path, seconds: int):
    records = []
    start = time.time()
    while time.time() - start < seconds:
        payload = {
            "block_id": f"00000000-0000-0000-0000-{int(time.time()*1000000)%10**12:012d}",
            "camera_id": "CAM_01",
            "cam_event_id": f"evt_{int(time.time()*1000)}",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            "plate_hash": "demo_hash",
            "plate_text_enc": "demo_enc",
            "conf": 0.91,
            "location": {"lat": 28.6139, "lon": 77.2090},
            "resolution": {
                "fused_as": "DEMO",
                "outcome": "single_channel",
                "vendor_guess": "DEMO",
                "alt_hashes": [],
            },
            "quality": "unverified",
        }
        records.append({"offset_s": round(time.time() - start, 3), "payload": payload})
        requests.post(f"{base_url}/ingest", json=payload, headers={"x-api-key": api_key}, timeout=5)
        time.sleep(0.8)
    out_file.write_text(json.dumps(records, indent=2))
    print(f"saved {len(records)} events to {out_file}")


def replay(base_url: str, api_key: str, in_file: Path):
    records = json.loads(in_file.read_text())
    start = time.time()
    for item in records:
        target = item["offset_s"]
        while time.time() - start < target:
            time.sleep(0.01)
        requests.post(f"{base_url}/ingest", json=item["payload"], headers={"x-api-key": api_key}, timeout=5)
    print(f"replayed {len(records)} events")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture and replay ingest events preserving order/timing")
    parser.add_argument("mode", choices=["record", "replay"])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--file", default="/tmp/sentinelgrid-replay.json")
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()

    path = Path(args.file)
    if args.mode == "record":
        record(args.base_url, args.api_key, path, args.seconds)
    else:
        replay(args.base_url, args.api_key, path)
