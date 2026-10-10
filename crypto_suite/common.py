"""Shared helpers: HKDF key derivation and AES-256-GCM authenticated encryption.

All three security modes end the same way: derive a 32-byte key from the raw
shared secret(s), then protect the data with AES-256-GCM. Only established
library primitives (`cryptography`) are used here -- no custom crypto.
"""
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEY_BYTES = 32      # AES-256
NONCE_BYTES = 12    # 96-bit GCM nonce (recommended size)
TAG_BYTES = 16      # GCM authentication tag appended by AESGCM.encrypt


def derive_key(secret: bytes, info: bytes = b"adaptive-crypto-v1") -> bytes:
    """Turn raw shared secret(s) into a clean 32-byte AES key."""
    return HKDF(algorithm=hashes.SHA256(), length=KEY_BYTES, salt=None, info=info).derive(secret)


def new_nonce() -> bytes:
    """Fresh nonce from the OS CSPRNG. Never reuse a nonce with the same key."""
    return os.urandom(NONCE_BYTES)


def encrypt(key: bytes, plaintext: bytes, aad: bytes | None = None) -> bytes:
    """AES-256-GCM encrypt. Output layout: nonce (12) || ciphertext || tag (16)."""
    nonce = new_nonce()
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def decrypt(key: bytes, blob: bytes, aad: bytes | None = None) -> bytes:
    """AES-256-GCM decrypt. Raises `cryptography.exceptions.InvalidTag` on wrong key or tampering."""
    return AESGCM(key).decrypt(blob[:NONCE_BYTES], blob[NONCE_BYTES:], aad)
