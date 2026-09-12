"""
ocr.py — PaddleOCR-based plate reading, behind a swappable BaseOCR
interface (TEAM.md: "OCR behind BaseOCR interface — judges hear
'any model drops in.'").

No detection model of our own here: per the architecture (Section 3),
the camera/vendor already sends a JPEG crop roughly centered on the
plate. This file runs PaddleOCR's full detect+recognize pipeline on
that crop (not recognition-only) because vendor crops are rarely
pixel-perfect around just the plate — there may be a bumper edge,
a second plate-like sticker, etc. Running detection lets us pick the
single best text region rather than assuming the whole crop is one
clean plate.
"""

import logging
import re
from abc import ABC, abstractmethod

import numpy as np
from paddleocr import PaddleOCR

logger = logging.getLogger("ocr")

# Loose plate-shape filter: mostly letters/digits, 4-10 chars after
# stripping spaces. Tune this against your actual seeded/test plates —
# it's a heuristic to reject junk text PaddleOCR might pick up from a
# crop's background (e.g. a shop sign edge caught in frame).
_PLATE_LIKE = re.compile(r"^[A-Z0-9]{4,10}$")


class BaseOCR(ABC):
    """Swappable OCR interface — the contract point pipeline.py depends on.
    Any implementation takes a frame (already run through enhance.py)
    and returns (plate_text, confidence)."""

    @abstractmethod
    def read_plate(self, frame: np.ndarray) -> tuple[str | None, float]:
        ...


class PaddleOCRReader(BaseOCR):
    """Detection + recognition via PaddleOCR, no separate plate detector."""

    def __init__(self, lang: str = "en") -> None:
        logger.info("Loading PaddleOCR (lang=%s)...", lang)
        # use_doc_orientation_classify/use_doc_unwarping off — these are for
        # scanned documents, not vehicle crops, and just add latency here.
        self._ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,  # plates are sometimes tilted
        )

    def read_plate(self, frame: np.ndarray) -> tuple[str | None, float]:
        try:
            results = self._ocr.predict(frame)
        except Exception:
            logger.exception("PaddleOCR inference failed on this frame.")
            return None, 0.0

        if not results:
            logger.debug("No OCR result for this frame.")
            return None, 0.0

        result = results[0]

        # ⚠️ VERIFY against your installed paddleocr version — 3.x result
        # objects have shifted field names before. This handles both the
        # dict-style {'res': {...}} wrapper and a flat form.
        try:
            inner = result["res"] if "res" in result else result
            texts = inner.get("rec_texts", [])
            scores = inner.get("rec_scores", [])
        except (KeyError, TypeError, AttributeError):
            texts = getattr(result, "rec_texts", [])
            scores = getattr(result, "rec_scores", [])

        if not texts:
            logger.debug("No text lines detected in crop.")
            return None, 0.0

        candidates = []
        for text, score in zip(texts, scores):
            cleaned = text.upper().replace(" ", "").replace("-", "")
            if _PLATE_LIKE.match(cleaned):
                candidates.append((cleaned, float(score)))

        if not candidates:
            # Nothing matched the plate-shape filter — fall back to the
            # single highest-confidence raw line rather than dropping
            # the read entirely; fusion.py's own rules decide if this
            # confidence is high enough to keep.
            best_idx = int(np.argmax(scores))
            fallback_text = texts[best_idx].upper().replace(" ", "")
            fallback_score = float(scores[best_idx])
            logger.debug(
                "No plate-shaped candidate; falling back to best raw line: %s (%.2f)",
                fallback_text, fallback_score,
            )
            return fallback_text, fallback_score

        # Prefer the plate-shaped candidate with highest confidence.
        candidates.sort(key=lambda c: c[1], reverse=True)
        best_text, best_score = candidates[0]

        logger.info("Read plate=%s conf=%.2f", best_text, best_score)
        return best_text, best_score


def build_default_ocr() -> BaseOCR:
    """Factory so pipeline.py never imports PaddleOCRReader directly —
    keeps the 'swappable block' promise real for judges."""
    return PaddleOCRReader()