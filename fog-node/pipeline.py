"""
SentinelGrid — fog-node/pipeline.py
The core executor. Replaces fog_sim.py for processing real images.
"""
import os
import cv2
import uuid
import requests
import logging
from datetime import datetime, timezone
from enhancement import enhance_plate
from ocr import run_ocr
from fusion import fuse_results
from buffer import save_to_buffer, flush_buffer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [pipeline] %(message)s")
log = logging.getLogger("pipeline")

API_URL = os.environ.get("API_URL", "http://localhost:8000/ingest")
FOG_API_KEY = os.environ.get("FOG_API_KEY", "hackathon_secret_key")

def process_frame(image_path: str, camera_id: str, lat: float, lon: float, vendor_guess: str = ""):
    log.info(f"Processing frame from {camera_id}...")
    
    # 1. Load and enhance
    raw_img = cv2.imread(image_path)
    if raw_img is None:
        log.error(f"Could not load image at {image_path}")
        return
        
    enhanced_img = enhance_plate(raw_img)
    
    # 2. Extract Text via PaddleOCR
    plate_text, conf = run_ocr(enhanced_img)
    
    # 3. Fuse logic
    resolution = fuse_results(plate_text, conf, vendor_guess)
    final_plate = resolution["fused_as"]
    
    if not final_plate:
        log.warning("No readable plate found. Dropping frame.")
        return

    # 4. Construct API Payload
    block = {
        "block_id": str(uuid.uuid4()),
        "camera_id": camera_id,
        "cam_event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "plate_text": final_plate,
        "conf": conf,
        "location": {"lat": lat, "lon": lon},
        "resolution": resolution,
        "quality": "verified" if conf > 0.90 else "unverified",
    }
    
    # 5. Transmit with fallback to local SQLite buffer
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {FOG_API_KEY}"}
    
    flush_buffer(API_URL, headers) # Try to flush any old offline data first
    
    try:
        resp = requests.post(API_URL, json=block, headers=headers, timeout=5)
        if resp.status_code == 200:
            log.info(f"SUCCESS: Plate {final_plate} transmitted to cloud.")
        else:
            log.warning(f"Cloud rejected block: {resp.text}")
            save_to_buffer(block)
    except requests.exceptions.RequestException:
        save_to_buffer(block)

if __name__ == "__main__":
    # Test execution for the demo
    # Ensure you drop a test image named 'car.jpg' in the fog-node folder
    test_image = "car.jpg" 
    
    if os.path.exists(test_image):
        # Setting fallback coordinates local to NIT Warangal for realistic map plotting
        process_frame(test_image, camera_id="CAM_01", lat=17.9835, lon=79.5308)
    else:
        log.error("Please place a 'car.jpg' file in the directory to run the pipeline test.")