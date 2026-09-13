"""
SentinelGrid — fog-node/ocr.py
Multi-engine OCR inference (PaddleOCR with seamless PyTorch/EasyOCR fallback for Python 3.14)
with strict Indian License Plate regex filtering:
^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$
"""

import os
import re
import logging
from typing import Tuple, List, Optional

log = logging.getLogger("ocr")

# Strict regex filter required by SentinelGrid architecture
STRICT_PLATE_REGEX = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$")
SUBSTRING_PLATE_REGEX = re.compile(r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}")

_paddle_engine = None
_easyocr_engine = None

def get_ocr_engine():
    global _paddle_engine, _easyocr_engine
    
    # 1. Try PaddleOCR first
    if _paddle_engine is None:
        try:
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            from paddleocr import PaddleOCR
            _paddle_engine = PaddleOCR(lang="en")
            log.info("Initialized PaddleOCR engine in CPU mode.")
            return ("paddle", _paddle_engine)
        except Exception as e:
            log.info(f"PaddleOCR not available ({e}). Falling back to EasyOCR (PyTorch CPU)...")
            _paddle_engine = False

    if _paddle_engine:
        return ("paddle", _paddle_engine)

    # 2. Fallback to EasyOCR (PyTorch CPU)
    if _easyocr_engine is None:
        try:
            import easyocr
            _easyocr_engine = easyocr.Reader(["en"], gpu=False)
            log.info("Initialized EasyOCR engine in CPU mode.")
            return ("easyocr", _easyocr_engine)
        except Exception as e:
            log.warning(f"EasyOCR not available: {e}")
            _easyocr_engine = False

    if _easyocr_engine:
        return ("easyocr", _easyocr_engine)

    return (None, None)

def sanitize_text(text: str) -> str:
    """Uppercase and strip special characters."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())

def validate_plate(candidate: str) -> Optional[str]:
    """
    Validates a text string against the strict Indian plate regex:
    ^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$
    Handles common HSRP artifacts like 'IND' country prefix.
    """
    cleaned = sanitize_text(candidate)
    
    # Check exact match
    if STRICT_PLATE_REGEX.match(cleaned):
        return cleaned

    # Strip 'IND' prefix if present on HSRP plates (e.g., INDMH12AB1284 -> MH12AB1284)
    if cleaned.startswith("IND"):
        without_ind = cleaned[3:]
        if STRICT_PLATE_REGEX.match(without_ind):
            return without_ind

    # Check for embedded matching substring
    match = SUBSTRING_PLATE_REGEX.search(cleaned)
    if match:
        return match.group(0)

    return None

def extract_plate_from_ocr_lines(lines: List[Tuple[str, float]]) -> Tuple[str, float]:
    """
    Takes a list of (text, confidence) tuples, validates against strict regex,
    and returns (plate_text, confidence).
    Discards any read that does not strictly match the regex.
    """
    if not lines:
        return "", 0.0

    valid_candidates: List[Tuple[str, float]] = []
    all_cleaned_texts: List[str] = []
    confidences: List[float] = []

    for text, conf in lines:
        cleaned = sanitize_text(text)
        if not cleaned:
            continue

        all_cleaned_texts.append(cleaned)
        confidences.append(float(conf))

        plate = validate_plate(cleaned)
        if plate:
            valid_candidates.append((plate, float(conf)))

    # If any individual line matched the strict regex, return highest confidence match
    if valid_candidates:
        valid_candidates.sort(key=lambda x: x[1], reverse=True)
        return valid_candidates[0]

    # In two-line plates, combine consecutive text chunks and re-validate
    combined = "".join(all_cleaned_texts)
    plate = validate_plate(combined)
    if plate:
        avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.85
        return plate, avg_conf

    log.info(f"Discarded non-matching OCR reads: {all_cleaned_texts}")
    return "", 0.0

def run_ocr(image_input) -> Tuple[str, float]:
    """
    Runs OCR on the provided image and applies strict regex filtering.
    Returns:
        (plate_text, confidence) if valid plate matched.
        ("", 0.0) if discarded as garbage or no plate found.
    """
    engine_type, engine = get_ocr_engine()
    if not engine:
        log.warning("No OCR engine available.")
        return "", 0.0

    try:
        lines: List[Tuple[str, float]] = []

        if engine_type == "paddle":
            results = engine.ocr(image_input, cls=True)
            if results and results[0]:
                for line in results[0]:
                    if line and len(line) >= 2:
                        lines.append((line[1][0], float(line[1][1])))

        elif engine_type == "easyocr":
            # EasyOCR expects numpy array or file path
            results = engine.readtext(image_input)
            for bbox, text, conf in results:
                lines.append((text, float(conf)))

        return extract_plate_from_ocr_lines(lines)

    except Exception as e:
        log.error(f"Error during OCR inference: {e}")
        return "", 0.0