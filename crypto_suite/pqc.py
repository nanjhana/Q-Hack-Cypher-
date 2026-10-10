"""Post-quantum key establishment: ML-KEM-768 (FIPS 203), hidden behind one `establish()`.

Backend selection (first one that works wins):

1. ``liboqs``       -- Open Quantum Safe via liboqs-python (spec Option A). Only tried if the
                       native liboqs shared library is actually present, because importing
                       ``oqs`` without it tries to git-clone + cmake-build liboqs and then raises
                       ``SystemExit`` (which a plain ``except Exception`` would not catch).
2. ``cryptography`` -- native ML-KEM-768 from the `cryptography` package (OpenSSL-backed,
                       hardened). Same library we already use for AES/X25519/HKDF.
3. ``kyber-py``     -- pure-Python educational implementation (spec Option B). NOT hardened /
                       not constant-time; timings are indicative only.

Force a specific backend with the environment variable ``PQC_BACKEND`` set to one of
``liboqs``, ``cryptography`` or ``kyber-py``.
"""
import ctypes.util
import os
from pathlib import Path

ALGORITHM = "ML-KEM-768"
BACKEND: str = ""          # human-readable label, e.g. "cryptography/OpenSSL (ML-KEM-768, hardened)"
BACKEND_ID: str = ""       # "liboqs" | "cryptography" | "kyber-py"
HARDENED: bool = False     # False only for the educational fallback
_establish_impl = None


def _liboqs_library_present() -> bool:
    install = Path(os.environ.get("OQS_INSTALL_PATH", str(Path.home() / "_oqs")))
    for d in (install / "lib", install / "lib64", install / "bin"):
        if d.is_dir() and any(p.name.startswith(("liboqs", "oqs")) for p in d.iterdir()):
            return True
    return ctypes.util.find_library("oqs") is not None


# --------------------------------------------------------------------------- backends
def _try_liboqs():
    if not _liboqs_library_present():
        raise ImportError("liboqs shared library not found")
    try:
        import oqs  # noqa: WPS433
    except BaseException as exc:  # liboqs-python raises SystemExit when it cannot load/build
        raise ImportError(f"liboqs-python unusable: {exc!r}") from None
    names = oqs.get_enabled_kem_mechanisms()
    kem_name = next(n for n in ("ML-KEM-768", "Kyber768") if n in names)

    def establish():
        with oqs.KeyEncapsulation(kem_name) as server:
            pk = server.generate_keypair()
            with oqs.KeyEncapsulation(kem_name) as client:
                ct, client_secret = client.encap_secret(pk)
            server_secret = server.decap_secret(ct)
        return client_secret, server_secret, pk, ct

    return establish, f"liboqs ({kem_name}, hardened)", True


def _try_cryptography():
    from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey, MLKEM768PublicKey

    MLKEM768PrivateKey.generate()  # raises UnsupportedAlgorithm if the OpenSSL build lacks ML-KEM

    def establish():
        server_sk = MLKEM768PrivateKey.generate()
        pk = server_sk.public_key().public_bytes_raw()              # server -> client
        client_secret, ct = MLKEM768PublicKey.from_public_bytes(pk).encapsulate()
        server_secret = server_sk.decapsulate(ct)                   # client -> server: ct
        return client_secret, server_secret, pk, ct

    return establish, "cryptography/OpenSSL (ML-KEM-768, hardened)", True


def _try_kyber_py():
    from kyber_py.ml_kem import ML_KEM_768

    def establish():
        pk, sk = ML_KEM_768.keygen()
        client_secret, ct = ML_KEM_768.encaps(pk)
        server_secret = ML_KEM_768.decaps(sk, ct)
        return client_secret, server_secret, pk, ct

    return establish, "kyber-py (ML-KEM-768, educational, NOT hardened)", False


_BACKENDS = {"liboqs": _try_liboqs, "cryptography": _try_cryptography, "kyber-py": _try_kyber_py}
SELECTION_LOG: list[str] = []   # why each backend was or was not chosen (shown in README/dashboard)


def _select():
    global BACKEND, BACKEND_ID, HARDENED, _establish_impl
    forced = os.environ.get("PQC_BACKEND", "").strip()
    order = [forced] if forced else list(_BACKENDS)
    for bid in order:
        if bid not in _BACKENDS:
            raise ValueError(f"Unknown PQC_BACKEND={bid!r}; choose from {list(_BACKENDS)}")
        try:
            impl, label, hardened = _BACKENDS[bid]()
        except Exception as exc:  # not installed / not built / algorithm missing
            SELECTION_LOG.append(f"{bid}: unavailable ({exc.__class__.__name__}: {exc})")
            continue
        SELECTION_LOG.append(f"{bid}: selected")
        BACKEND, BACKEND_ID, HARDENED, _establish_impl = label, bid, hardened, impl
        return
    raise ImportError("No ML-KEM-768 backend available. Install `cryptography>=50` or `kyber-py`.\n"
                      + "\n".join(SELECTION_LOG))


_select()


def establish():
    """Returns (shared_secret, bytes_on_wire). Server publishes pk, client replies with ciphertext."""
    client_secret, server_secret, pk, ct = _establish_impl()
    if client_secret != server_secret:
        raise RuntimeError("ML-KEM shared secrets do not match")
    return client_secret, len(pk) + len(ct)
