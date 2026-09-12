import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _read_key(name: str, min_len: int) -> bytes:
    raw = os.getenv(name, "")
    if not raw:
        raise RuntimeError(f"Missing env {name}")
    key = base64.b64decode(raw)
    if len(key) < min_len:
        raise RuntimeError(f"{name} too short")
    return key


def hmac_plate(text: str) -> str:
    # Rule 4: plain SHA-256 for plate-derived identifiers is banned; use HMAC-SHA256.
    key = _read_key("HMAC_KEY", 32)
    return hmac.new(key, text.strip().upper().encode(), hashlib.sha256).hexdigest()


def encrypt_plate(text: str) -> str:
    key = _read_key("AES_KEY", 32)
    if len(key) != 32:
        raise RuntimeError("AES_KEY must decode to exactly 32 bytes")
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aes.encrypt(nonce, text.strip().upper().encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_plate(blob_b64: str) -> str:
    key = _read_key("AES_KEY", 32)
    aes = AESGCM(key)
    blob = base64.b64decode(blob_b64)
    nonce, ciphertext = blob[:12], blob[12:]
    return aes.decrypt(nonce, ciphertext, None).decode()
