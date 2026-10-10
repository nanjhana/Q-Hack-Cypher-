"""Hybrid key establishment: X25519 + ML-KEM-768 together.

The final AES key is derived (via HKDF in `suite.py`) from BOTH secrets, so an
attacker has to break both X25519 and ML-KEM-768 to recover it.
"""
from . import classical, pqc

ALGORITHM = "X25519 + ML-KEM-768"


def establish():
    """Returns (combined_raw_secret, bytes_on_wire)."""
    c_secret, c_bytes = classical.establish()
    p_secret, p_bytes = pqc.establish()
    combined = c_secret + p_secret                   # attacker needs BOTH to recover the key
    return combined, c_bytes + p_bytes
