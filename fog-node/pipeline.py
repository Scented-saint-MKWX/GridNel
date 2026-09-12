from datetime import datetime, timezone
from uuid import uuid4

from auth.hashing import encrypt_plate, hmac_plate
from enhance import enhance_crop
from fusion import resolve
from ocr import PaddleOCRImpl


def pipeline(image, vendor_guess: str | None, camera_id: str, lat: float, lon: float, cam_event_id: str):
    # Rule 1: crop is processed in-memory only and never written to disk.
    ocr = PaddleOCRImpl()
    enhanced = enhance_crop(image, low_quality=False)
    engine_read, engine_conf = ocr.read(enhanced)
    vendor_conf = 0.90 if vendor_guess else 0.0
    fused = resolve(vendor_guess, vendor_conf, engine_read, engine_conf)

    if not fused.plate:
        return None

    alt_hashes = [hmac_plate(x) for x in fused.rejected if x and x != fused.plate]
    plate_hash = hmac_plate(fused.plate)
    block = {
        "block_id": str(uuid4()),
        "camera_id": camera_id,
        "cam_event_id": cam_event_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "plate_hash": plate_hash,
        "plate_text_enc": encrypt_plate(fused.plate),
        "conf": round(float(fused.conf), 3),
        "location": {"lat": lat, "lon": lon},
        "resolution": {
            "fused_as": fused.plate,
            "outcome": fused.outcome,
            "vendor_guess": vendor_guess,
            "alt_hashes": alt_hashes,
        },
        "quality": "full_pipeline",
    }
    return block, fused.outcome
