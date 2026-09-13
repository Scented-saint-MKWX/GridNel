"""Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
Reconstructed from TEAM.md's frozen contract (HMAC hash, AES-GCM encrypt) since
the real auth/hashing.py was never committed. Keys come from env only, never
hardcoded — TEAM.md §4.2 / §11 (plain SHA-256 is banned; HMAC or nothing).
"""
import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HMAC_KEY = os.environ["HMAC_KEY"].encode()
AES_KEY = base64.b64decode(os.environ["AES_KEY"])


def hmac_plate(plate_text: str) -> str:
    return hmac.new(HMAC_KEY, plate_text.upper().encode(), hashlib.sha256).hexdigest()


def encrypt_plate(plate_text: str) -> str:
    aesgcm = AESGCM(AES_KEY)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plate_text.upper().encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_plate(encoded: str) -> str:
    raw = base64.b64decode(encoded)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(AES_KEY)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
