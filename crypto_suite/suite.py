"""One entry point for all three security modes: `establish(mode)` and `secure_roundtrip(mode, data)`."""
import time

from . import classical, hybrid, pqc
from .common import decrypt, derive_key, encrypt

MODES = ("CLASSICAL", "QUANTUM_SAFE", "HYBRID")
_ESTABLISH = {"CLASSICAL": classical.establish, "QUANTUM_SAFE": pqc.establish, "HYBRID": hybrid.establish}

ALGORITHMS = {
    "CLASSICAL": "X25519 + AES-256-GCM",
    "QUANTUM_SAFE": "ML-KEM-768 + AES-256-GCM",
    "HYBRID": "X25519 + ML-KEM-768 + AES-256-GCM",
}


def _check(mode: str) -> None:
    if mode not in _ESTABLISH:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {MODES}")


def establish(mode: str):
    """Run real key establishment for `mode`. Returns (aes_key, handshake_bytes, handshake_ms)."""
    _check(mode)
    t0 = time.perf_counter()
    secret, wire_bytes = _ESTABLISH[mode]()
    key = derive_key(secret, info=b"adaptive-crypto-v1|" + mode.encode())   # per-mode domain separation
    ms = (time.perf_counter() - t0) * 1000
    return key, wire_bytes, ms


def secure_roundtrip(mode: str, plaintext: bytes) -> dict:
    """Establish a key, AES-256-GCM encrypt, decrypt, and report real timings and sizes."""
    key, wire_bytes, hs_ms = establish(mode)
    t0 = time.perf_counter(); blob = encrypt(key, plaintext); enc_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter(); out = decrypt(key, blob);      dec_ms = (time.perf_counter() - t0) * 1000
    return {"mode": mode, "algorithms": ALGORITHMS[mode],
            "pqc_backend": pqc.BACKEND if mode != "CLASSICAL" else "n/a",
            "handshake_ms": hs_ms, "handshake_bytes": wire_bytes,
            "encrypt_ms": enc_ms, "decrypt_ms": dec_ms,
            "plaintext_bytes": len(plaintext), "ciphertext_bytes": len(blob),
            "ciphertext_preview": blob[:24].hex(),
            "correct": out == plaintext}
