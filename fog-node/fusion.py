"""
SentinelGrid — fog-node/fusion.py
Resolves conflicts between the Edge OCR engine and Camera Vendor hardware.
"""

def fuse_results(engine_text: str, engine_conf: float, vendor_guess: str) -> dict:
    # If the edge engine completely failed to read anything
    if not engine_text:
        return {
            "fused_as": vendor_guess,
            "outcome": "vendor_preferred",
            "vendor_guess": vendor_guess,
            "alt_texts": []
        }
        
    # Total agreement
    if engine_text == vendor_guess:
        return {
            "fused_as": engine_text,
            "outcome": "agreement",
            "vendor_guess": vendor_guess,
            "alt_texts": []
        }
        
    # Conflict: Trust our Edge Engine if confidence is high
    if engine_conf > 0.85:
        return {
            "fused_as": engine_text,
            "outcome": "engine_preferred",
            "vendor_guess": vendor_guess,
            "alt_texts": [vendor_guess] if vendor_guess else []
        }
        
    # Conflict: Engine confidence is low, fallback to vendor
    return {
        "fused_as": vendor_guess,
        "outcome": "low_confidence_fallback",
        "vendor_guess": vendor_guess,
        "alt_texts": [engine_text]
    }