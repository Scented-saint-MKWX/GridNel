"""
SentinelGrid — scripts/run_dataset.py
Batch evaluates an image dataset against the YOLOv8 + PaddleOCR + Regex pipeline.
Generates structured JSON evaluation reports and optionally ingests valid reads into the cloud.
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path

# Add project root and fog-node to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "fog-node"))

from pipeline import process_frame

logging.basicConfig(level=logging.INFO, format="%(asctime)s [run_dataset] %(levelname)s: %(message)s")
log = logging.getLogger("run_dataset")

def run_dataset_evaluation(
    input_dir: str,
    manifest_path: str | None = None,
    output_path: str = "output/dataset_evaluation.json",
    ingest: bool = False,
    camera_id: str = "CAM_01"
) -> dict:
    image_dir = Path(input_dir)
    if not image_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    manifest = {}
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

    image_extensions = {".jpg", ".jpeg", ".png"}
    image_files = sorted([f for f in image_dir.iterdir() if f.suffix.lower() in image_extensions])

    if not image_files:
        log.warning(f"No image files found in {input_dir}")
        return {}

    log.info(f"Processing dataset of {len(image_files)} images from: {input_dir}")
    
    results = []
    total_valid = 0
    total_discarded = 0
    total_correct = 0
    latencies = []

    for img_path in image_files:
        fname = img_path.name
        expected = manifest.get(fname, {}).get("ground_truth", None) if manifest else None
        
        t0 = time.perf_counter()
        block = process_frame(
            image_path=str(img_path),
            camera_id=camera_id,
            send_to_cloud=ingest
        )
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        latencies.append(latency_ms)

        if block and block.get("plate_text"):
            detected = block["plate_text"]
            conf = block["conf"]
            status = "VALID_PLATE"
            total_valid += 1
            is_match = (detected == expected) if expected else None
            if is_match:
                total_correct += 1
        else:
            detected = None
            conf = 0.0
            status = "DISCARDED_GARBAGE"
            total_discarded += 1
            is_match = (expected is None) if expected else None
            if is_match:
                total_correct += 1

        log.info(f"[{fname}] {status} -> Read: {detected} | Expected: {expected} | {latency_ms}ms")
        
        results.append({
            "image": fname,
            "status": status,
            "detected_plate": detected,
            "expected_plate": expected,
            "confidence": conf,
            "latency_ms": latency_ms,
            "matches_expected": is_match
        })

    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    accuracy = round(total_correct / len(image_files) * 100, 2) if manifest else None

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_directory": str(input_dir),
        "total_images": len(image_files),
        "valid_plates_passed": total_valid,
        "garbage_reads_discarded": total_discarded,
        "average_latency_ms": avg_latency,
        "manifest_used": bool(manifest),
        "accuracy_percentage": accuracy,
        "detailed_results": results
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    log.info(f"Dataset processing complete. Output saved to: {output_path}")
    log.info(f"Summary: {total_valid} Valid Plates | {total_discarded} Garbage Discarded | Avg Latency: {avg_latency}ms")
    
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate image dataset against SentinelGrid AI pipeline")
    parser.add_argument("--input-dir", default="data/sample_images", help="Directory containing images")
    parser.add_argument("--manifest", default="data/sample_images/manifest.json", help="Optional ground truth JSON")
    parser.add_argument("--output", default="output/dataset_evaluation.json", help="Output JSON report")
    parser.add_argument("--ingest", action="store_true", help="Stream valid plates to API")
    parser.add_argument("--camera", default="CAM_01", help="Camera ID to simulate")
    args = parser.parse_args()

    run_dataset_evaluation(
        input_dir=args.input_dir,
        manifest_path=args.manifest if os.path.exists(args.manifest) else None,
        output_path=args.output,
        ingest=args.ingest,
        camera_id=args.camera
    )

