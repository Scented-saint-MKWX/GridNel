"""
SentinelGrid — scripts/ingest_kaggle_dataset.py
Allows users to input a Kaggle dataset (via Kaggle slug or local unzipped directory),
runs the Edge AI pipeline (YOLOv8 + OCR + strict Indian License Plate regex filtering),
streams detections to the SentinelGrid API, and generates a structured output report.
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path

# Add project root and fog-node to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "fog-node"))

from pipeline import process_frame

logging.basicConfig(level=logging.INFO, format="%(asctime)s [kaggle_ingest] %(levelname)s: %(message)s")
log = logging.getLogger("kaggle_ingest")

def resolve_kaggle_dataset(dataset_input: str) -> str:
    """
    If dataset_input is an existing local directory, returns it directly.
    Otherwise, treats it as a Kaggle slug (e.g. 'owner/dataset-name') and downloads via kagglehub.
    """
    if os.path.isdir(dataset_input):
        log.info(f"Using local Kaggle dataset directory: {dataset_input}")
        return dataset_input

    log.info(f"Downloading Kaggle dataset '{dataset_input}' via kagglehub...")
    try:
        import kagglehub
        path = kagglehub.dataset_download(dataset_input)
        log.info(f"Dataset successfully downloaded to: {path}")
        return path
    except Exception as e:
        log.error(f"Failed to download dataset via kagglehub: {e}")
        raise

def process_kaggle_dataset(
    dataset_input: str,
    limit: int = 25,
    output_path: str = "output/kaggle_dataset_output.json",
    ingest: bool = True,
    camera_id: str = "CAM_01"
) -> dict:
    dataset_dir = resolve_kaggle_dataset(dataset_input)
    root_path = Path(dataset_dir)

    # Collect all image files recursively
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    image_files = []
    for ext in image_extensions:
        image_files.extend(root_path.rglob(f"*{ext}"))
        image_files.extend(root_path.rglob(f"*{ext.upper()}"))

    image_files = sorted(list(set(image_files)))
    total_found = len(image_files)

    if total_found == 0:
        log.warning(f"No image files found in {dataset_dir}")
        return {"error": "No images found", "dataset_dir": dataset_dir}

    if limit > 0 and limit < total_found:
        log.info(f"Found {total_found} images. Processing first {limit} (use --limit 0 for all)...")
        image_files = image_files[:limit]
    else:
        log.info(f"Processing all {total_found} images from dataset...")

    results = []
    valid_plates = []
    garbage_discarded = 0
    latencies = []
    blacklist_hits = []

    for idx, img_file in enumerate(image_files):
        rel_path = str(img_file.relative_to(root_path))
        t0 = time.perf_counter()

        block = process_frame(
            image_path=str(img_file),
            camera_id=camera_id,
            send_to_cloud=ingest
        )
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        latencies.append(latency_ms)

        if block and block.get("plate_text"):
            plate = block["plate_text"]
            conf = block["conf"]
            status = "VALID_PLATE"
            valid_plates.append(plate)
            
            # Check if this plate matches our known blacklist demo target
            if plate == "MH12AB1284":
                blacklist_hits.append(plate)
                
            log.info(f"[{idx+1}/{len(image_files)}] {rel_path} -> MATCH: {plate} (conf: {conf}, {latency_ms}ms)")
        else:
            plate = None
            conf = 0.0
            status = "DISCARDED_GARBAGE"
            garbage_discarded += 1
            log.info(f"[{idx+1}/{len(image_files)}] {rel_path} -> DISCARDED (No plate matching strict regex, {latency_ms}ms)")

        results.append({
            "image": rel_path,
            "status": status,
            "detected_plate": plate,
            "confidence": conf,
            "latency_ms": latency_ms
        })

    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_input": dataset_input,
        "dataset_directory": str(dataset_dir),
        "total_images_scanned": len(image_files),
        "valid_plates_extracted": len(valid_plates),
        "garbage_reads_discarded": garbage_discarded,
        "average_latency_ms": avg_latency,
        "unique_plates": sorted(list(set(valid_plates))),
        "blacklist_alerts_detected": blacklist_hits,
        "detailed_results": results
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    log.info("=" * 60)
    log.info("KAGGLE DATASET PROCESSING SUMMARY")
    log.info("=" * 60)
    log.info(f"Dataset:              {dataset_input}")
    log.info(f"Images Processed:     {len(image_files)}")
    log.info(f"Valid Plates:         {len(valid_plates)}")
    log.info(f"Garbage Discarded:    {garbage_discarded}")
    log.info(f"Average Latency:      {avg_latency} ms")
    log.info(f"Output Report:        {output_path}")
    log.info("=" * 60)

    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Kaggle dataset with SentinelGrid Edge AI")
    parser.add_argument("dataset", help="Kaggle dataset slug (e.g. 'owner/dataset') or path to local directory")
    parser.add_argument("--limit", type=int, default=20, help="Number of images to process (0 for all)")
    parser.add_argument("--output", default="output/kaggle_dataset_output.json", help="Path to output JSON")
    parser.add_argument("--no-ingest", action="store_true", help="Do not stream results to cloud API")
    parser.add_argument("--camera", default="CAM_01", help="Camera ID to associate with sightings")
    args = parser.parse_args()

    process_kaggle_dataset(
        dataset_input=args.dataset,
        limit=args.limit,
        output_path=args.output,
        ingest=not args.no_ingest,
        camera_id=args.camera
    )

