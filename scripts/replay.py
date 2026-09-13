"""
SentinelGrid — scripts/replay.py
Replays multi-camera vehicle trajectory datasets into the SentinelGrid ingestion API.
Generates reconstructed trajectory summaries and logs blacklist alert triggers.
"""

import os
import sys
import time
import json
import uuid
import logging
import argparse
import requests
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [replay] %(levelname)s: %(message)s")
log = logging.getLogger("replay")

API_URL = os.environ.get("API_URL", "http://localhost:8000/ingest")
FOG_API_KEY = os.environ.get("FOG_API_KEY", "hackathon_secret_key")

def load_dataset(dataset_path: str) -> list[dict]:
    with open(dataset_path, "r") as f:
        return json.load(f)

def replay_dataset(
    dataset_path: str,
    api_url: str = API_URL,
    delay: float = 0.5,
    output_path: str = "output/replay_summary.json"
) -> dict:
    trajectories = load_dataset(dataset_path)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FOG_API_KEY}"
    }

    log.info(f"Starting trajectory replay from {dataset_path} ({len(trajectories)} vehicle routes)...")
    
    total_events = 0
    successful_events = 0
    failed_events = 0
    vehicle_summaries = {}

    start_time = datetime.now(timezone.utc)
    base_ts = start_time - timedelta(minutes=15)

    for traj_idx, traj in enumerate(trajectories):
        plate = traj["plate_text"]
        is_blacklist = traj.get("is_blacklist", False)
        route = traj.get("route", [])
        
        log.info(f"[{traj_idx+1}/{len(trajectories)}] Replaying route for plate {plate} ({len(route)} stops)...")
        
        route_hops = []
        hop_time = base_ts + timedelta(minutes=traj_idx * 2)

        for hop_idx, stop in enumerate(route):
            total_events += 1
            cam_id = stop["camera_id"]
            lat = stop["lat"]
            lon = stop["lon"]
            conf = stop.get("conf", 0.95)
            
            hop_time += timedelta(seconds=stop.get("delta_seconds", 30))
            
            block = {
                "block_id": str(uuid.uuid4()),
                "camera_id": cam_id,
                "cam_event_id": f"evt_{uuid.uuid4().hex[:8]}",
                "ts": hop_time.isoformat(),
                "plate_text": plate,
                "conf": conf,
                "location": {"lat": lat, "lon": lon},
                "resolution": {
                    "fused_as": plate,
                    "outcome": "dataset_replay",
                    "vendor_guess": plate,
                    "alt_hashes": []
                },
                "quality": "verified"
            }

            try:
                resp = requests.post(api_url, json=block, headers=headers, timeout=5)
                if resp.status_code == 200:
                    successful_events += 1
                    status = "200 OK"
                else:
                    failed_events += 1
                    status = f"Rejected ({resp.status_code})"
            except Exception as e:
                failed_events += 1
                status = f"Error: {e}"

            log.info(f"  -> Stop #{hop_idx+1} {cam_id} @ {hop_time.strftime('%H:%M:%S')} - {status}")
            route_hops.append({
                "camera_id": cam_id,
                "lat": lat,
                "lon": lon,
                "ts": hop_time.isoformat(),
                "status": status
            })

            if delay > 0:
                time.sleep(delay)

        vehicle_summaries[plate] = {
            "is_blacklist": is_blacklist,
            "total_hops": len(route),
            "start_node": route[0]["camera_id"] if route else None,
            "end_node": route[-1]["camera_id"] if route else None,
            "route_detail": route_hops
        }

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_file": dataset_path,
        "total_vehicles": len(trajectories),
        "total_events": total_events,
        "successful_events": successful_events,
        "failed_events": failed_events,
        "vehicles": vehicle_summaries
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    log.info(f"Replay complete! Summary generated at: {output_path}")
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replay trajectory dataset into SentinelGrid")
    parser.add_argument("--dataset", default="data/trajectories.json", help="Path to trajectories.json")
    parser.add_argument("--url", default=API_URL, help="Target API URL")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between sightings in seconds")
    parser.add_argument("--output", default="output/replay_summary.json", help="Output summary report path")
    args = parser.parse_args()

    replay_dataset(args.dataset, args.url, args.delay, args.output)

