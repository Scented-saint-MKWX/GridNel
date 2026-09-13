"""
SentinelGrid — fog-node/pipeline.py
The core edge executor. Uses YOLOv8 for vehicle/plate localization,
PaddleOCR for text extraction, and strict Regex validation.
"""

import os
import sys
import uuid
import logging
import argparse
import requests
from datetime import datetime, timezone
import cv2
import numpy as np

# Ensure local imports work whether run from repo root or fog-node directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhancement import enhance_plate
from ocr import run_ocr, validate_plate
from fusion import fuse_results
from buffer import save_to_buffer, flush_buffer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [pipeline] %(levelname)s: %(message)s")
log = logging.getLogger("pipeline")

API_URL = os.environ.get("API_URL", "http://localhost:8000/ingest")
FOG_API_KEY = os.environ.get("FOG_API_KEY", "hackathon_secret_key")

_yolo_model = None

def get_yolo_model():
    """Lazy load YOLOv8 in CPU mode for WSL compatibility."""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Lightweight YOLOv8 nano model
            _yolo_model = YOLO("yolov8n.pt")
            log.info("Initialized YOLOv8 model in CPU mode.")
        except Exception as e:
            log.warning(f"Could not load YOLOv8 model: {e}. Falling back to direct frame OCR.")
            _yolo_model = False
    return _yolo_model

def detect_vehicle_crops(image_bgr) -> list:
    """
    Runs YOLOv8 vehicle detection and returns candidate crops (vehicle / plate regions).
    COCO vehicle classes: 2 (car), 3 (motorcycle), 5 (bus), 7 (truck).
    """
    model = get_yolo_model()
    crops = []
    
    if model:
        try:
            results = model(image_bgr, device="cpu", verbose=False)
            h, w = image_bgr.shape[:2]
            vehicle_classes = {2, 3, 5, 7}

            if results and len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    
                    if cls_id in vehicle_classes and conf > 0.25:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        # Clamp coordinates
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)
                        
                        if x2 > x1 and y2 > y1:
                            vehicle_crop = image_bgr[y1:y2, x1:x2]
                            # Plates are typically located in the lower 50% of the vehicle
                            vh, vw = vehicle_crop.shape[:2]
                            lower_crop = vehicle_crop[int(vh * 0.45):, :]
                            
                            crops.append(lower_crop)
                            crops.append(vehicle_crop)
        except Exception as e:
            log.warning(f"YOLO detection exception: {e}")

    # If no vehicles detected or YOLO unavailable, analyze full image
    if not crops:
        crops.append(image_bgr)

    return crops

def process_frame(
    image_path: str,
    camera_id: str = "CAM_01",
    lat: float = 28.6139,
    lon: float = 77.2090,
    vendor_guess: str = "",
    send_to_cloud: bool = True
) -> dict | None:
    """
    Full Edge AI Pipeline:
    1. Reads frame
    2. Localizes vehicle/plate regions with YOLOv8
    3. Enhances image (CLAHE, bilateral filter)
    4. Extracts text via PaddleOCR
    5. Discards non-matching garbage reads via strict Regex
    6. Fuses readings and POSTs payload to SentinelGrid API
    """
    log.info(f"Processing frame {image_path} from camera {camera_id}...")
    
    if not os.path.exists(image_path):
        log.error(f"Image not found at {image_path}")
        return None

    raw_img = cv2.imread(image_path)
    if raw_img is None:
        log.error(f"Failed to decode image at {image_path}")
        return None

    # Step 1: Detect candidate vehicle/plate regions using YOLOv8
    candidate_crops = detect_vehicle_crops(raw_img)
    
    detected_plate = ""
    best_conf = 0.0

    # Step 2 & 3: Enhance and OCR candidate crops
    for crop in candidate_crops:
        enhanced = enhance_plate(crop)
        plate, conf = run_ocr(enhanced)
        if plate:
            detected_plate = plate
            best_conf = conf
            break
        # Also try direct crop without enhancement
        plate, conf = run_ocr(crop)
        if plate:
            detected_plate = plate
            best_conf = conf
            break

    # Step 4: Strict Regex Validation check (guaranteed by run_ocr, double-checked here)
    if not detected_plate or not validate_plate(detected_plate):
        log.info(f"No valid Indian license plate matched strict regex for {image_path}. Frame discarded.")
        return None

    log.info(f"Validated Plate Detected: {detected_plate} (Confidence: {best_conf:.2f})")

    # Step 5: Hardware & OCR Fusion
    resolution = fuse_results(detected_plate, best_conf, vendor_guess)
    final_plate = resolution.get("fused_as", detected_plate)

    # Step 6: Construct JSON telemetry payload
    block = {
        "block_id": str(uuid.uuid4()),
        "camera_id": camera_id,
        "cam_event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "plate_text": final_plate,
        "conf": round(best_conf, 2),
        "location": {"lat": lat, "lon": lon},
        "resolution": resolution,
        "quality": "verified" if best_conf >= 0.85 else "unverified",
    }

    if not send_to_cloud:
        return block

    # Step 7: Transmit to Central Cloud API with local SQLite buffering on failure
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FOG_API_KEY}"
    }

    # Attempt to flush buffered records first
    flush_buffer(API_URL, headers)

    try:
        resp = requests.post(API_URL, json=block, headers=headers, timeout=5)
        if resp.status_code == 200:
            log.info(f"TRANSMITTED: Sighting for {final_plate} successfully pushed to Cloud.")
        else:
            log.warning(f"Cloud rejected block ({resp.status_code}): {resp.text}")
            save_to_buffer(block)
    except requests.exceptions.RequestException as e:
        log.warning(f"Cloud unreachable ({e}). Saving to offline buffer.")
        save_to_buffer(block)

    return block

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelGrid Edge AI Pipeline")
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("--camera", default="CAM_01", help="Camera ID")
    parser.add_argument("--lat", type=float, default=28.6139, help="Camera Latitude")
    parser.add_argument("--lon", type=float, default=77.2090, help="Camera Longitude")
    parser.add_argument("--vendor", default="", help="Optional camera vendor reading")
    args = parser.parse_args()

    result = process_frame(
        image_path=args.image,
        camera_id=args.camera,
        lat=args.lat,
        lon=args.lon,
        vendor_guess=args.vendor
    )
    if result:
        print(f"Result: {result['plate_text']} (conf={result['conf']})")
    else:
        print("No valid plate detected.")