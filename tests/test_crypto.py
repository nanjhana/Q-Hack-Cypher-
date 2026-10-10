"""Cryptographic correctness tests: real keys, real AES-256-GCM."""
import os

import pytest
from cryptography.exceptions import InvalidTag

from crypto_suite import classical, hybrid, pqc
from crypto_suite.common import NONCE_BYTES, TAG_BYTES, decrypt, derive_key, encrypt
from crypto_suite.suite import MODES, establish, secure_roundtrip


@pytest.mark.parametrize("mode", MODES)
def test_every_mode_establishes_a_key(mode):
    key, wire, ms = establish(mode)
    assert len(key) == 32 and wire > 0 and ms >= 0


def test_handshake_byte_sizes():
    # FIPS 203 ML-KEM-768: pk 1184 B, ct 1088 B; X25519: 32 B each way.
    assert classical.establish()[1] == 64
    assert pqc.establish()[1] == 1184 + 1088
    assert hybrid.establish()[1] == 64 + 1184 + 1088


@pytest.mark.parametrize("mode", MODES)
def test_roundtrip(mode):
    r = secure_roundtrip(mode, b"secret " * 50)
    assert r["correct"] is True
    assert r["ciphertext_bytes"] == len(b"secret " * 50) + NONCE_BYTES + TAG_BYTES


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("data", [b"", b"x", os.urandom(1), os.urandom(100_000), "héllo ✓".encode()])
def test_plaintext_recovered_exactly(mode, data):
    key, _, _ = establish(mode)
    assert decrypt(key, encrypt(key, data)) == data


@pytest.mark.parametrize("mode", MODES)
def test_fresh_keys_each_handshake(mode):
    assert establish(mode)[0] != establish(mode)[0]


@pytest.mark.parametrize("mode", MODES)
def test_wrong_key_fails(mode):
    key, _, _ = establish(mode); other, _, _ = establish(mode)
    with pytest.raises(InvalidTag):
        decrypt(other, encrypt(key, b"x"))


@pytest.mark.parametrize("position", [0, NONCE_BYTES, -1])   # nonce, ciphertext body, tag
def test_tamper_detected(position):
    key, _, _ = establish("CLASSICAL"); blob = bytearray(encrypt(key, b"hello world"))
    blob[position] ^= 1
    with pytest.raises(InvalidTag):
        decrypt(key, bytes(blob))


def test_nonce_is_fresh_per_message():
    key = os.urandom(32)
    a, b = encrypt(key, b"same"), encrypt(key, b"same")
    assert a[:NONCE_BYTES] != b[:NONCE_BYTES] and a != b


def test_hkdf_derives_32_bytes_and_separates_contexts():
    s = os.urandom(32)
    assert len(derive_key(s)) == 32
    assert derive_key(s, b"a") != derive_key(s, b"b")


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        establish("QUANTUM_MAGIC")


def test_pqc_backend_is_labelled():
    assert pqc.BACKEND and pqc.BACKEND_ID in ("liboqs", "cryptography", "kyber-py")
    if pqc.BACKEND_ID == "kyber-py":
        assert not pqc.HARDENED and "educational" in pqc.BACKEND
