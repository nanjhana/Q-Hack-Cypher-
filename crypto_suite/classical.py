"""Classical key establishment: X25519 (elliptic-curve Diffie-Hellman).

Both "client" and "server" run in one process (Round 1 is a local prototype);
we also count the bytes that would travel over the network.
"""
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ALGORITHM = "X25519"


def _raw(pub) -> bytes:
    return pub.public_bytes(Encoding.Raw, PublicFormat.Raw)


def server_start():
    priv = X25519PrivateKey.generate()
    return priv, _raw(priv.public_key())            # (private, public bytes to send)


def client_respond(server_pub: bytes):
    priv = X25519PrivateKey.generate()
    secret = priv.exchange(X25519PublicKey.from_public_bytes(server_pub))
    return secret, _raw(priv.public_key())          # (client's secret, bytes to send back)


def server_finish(priv, client_pub: bytes) -> bytes:
    return priv.exchange(X25519PublicKey.from_public_bytes(client_pub))


def establish():
    """Returns (raw_shared_secret, bytes_on_wire)."""
    s_priv, s_pub = server_start()
    c_secret, c_pub = client_respond(s_pub)
    s_secret = server_finish(s_priv, c_pub)
    if c_secret != s_secret:
        raise RuntimeError("X25519 shared secrets do not match")
    return c_secret, len(s_pub) + len(c_pub)
