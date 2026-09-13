"""
SentinelGrid — fog-node/edge_watcher.py
Uses watchdog to monitor fog-node/images/ directory.
When a new image is dropped in, triggers pipeline.py and POSTs payload to cloud.
"""

import os
import sys
import time
import logging
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pipeline import process_frame

logging.basicConfig(level=logging.INFO, format="%(asctime)s [edge_watcher] %(levelname)s: %(message)s")
log = logging.getLogger("edge_watcher")

WATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
CAMERAS_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "cameras.json")

def get_camera_info(filename: str) -> tuple[str, float, float]:
    """
    Resolves camera coordinates. If filename starts with a camera ID (e.g. CAM_03_car.jpg),
    it pulls lat/lon from db/cameras.json; otherwise defaults to CAM_01.
    """
    default_cam = ("CAM_01", 28.6139, 77.2090)
    if not os.path.exists(CAMERAS_JSON):
        return default_cam

    try:
        with open(CAMERAS_JSON, "r") as f:
            cameras = json.load(f)
            cam_map = {c["camera_id"]: (c["camera_id"], c["lat"], c["lon"]) for c in cameras}
            for cam_id in cam_map:
                if filename.upper().startswith(cam_id):
                    return cam_map[cam_id]
    except Exception as e:
        log.warning(f"Could not parse cameras.json: {e}")

    return default_cam

class ImageDropHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.processed = set()

    def process_image(self, file_path: str):
        if not file_path.lower().endswith((".jpg", ".jpeg", ".png")):
            return

        if file_path in self.processed:
            return

        # Debounce: wait for file write / copy to stabilize
        time.sleep(0.5)
        
        # Verify file exists and is non-empty
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return

        self.processed.add(file_path)
        filename = os.path.basename(file_path)
        cam_id, lat, lon = get_camera_info(filename)
        
        log.info(f"New image detected: {filename} -> Triggering AI Edge Pipeline on {cam_id}...")
        try:
            result = process_frame(
                image_path=file_path,
                camera_id=cam_id,
                lat=lat,
                lon=lon,
                send_to_cloud=True
            )
            if result:
                log.info(f"Pipeline finished for {filename}: Matched Plate {result['plate_text']}")
            else:
                log.info(f"Pipeline finished for {filename}: No valid plate / discarded garbage.")
        except Exception as e:
            log.error(f"Error processing image {filename}: {e}", exc_info=True)

    def on_created(self, event):
        if not event.is_directory:
            self.process_image(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.process_image(event.dest_path)

def start_watcher():
    os.makedirs(WATCH_DIR, exist_ok=True)
    event_handler = ImageDropHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIR, recursive=False)
    observer.start()
    log.info(f"Edge Watcher active. Monitoring folder: {WATCH_DIR}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping Edge Watcher...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watcher()

