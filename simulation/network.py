"""Simple (SIMULATED) network model: estimated transfer time = bytes / bandwidth.

The crypto timings plugged into this model are REAL (from benchmarking/results.json);
the network link itself is simulated.
"""

MIN_BANDWIDTH_KBPS = 1e-6   # guards against division by zero for extreme inputs


def transfer_ms(num_bytes: int, bandwidth_kbps: float) -> float:
    """Time to push bytes through a link of given bandwidth."""
    return (num_bytes * 8) / (max(bandwidth_kbps, MIN_BANDWIDTH_KBPS) * 1000) * 1000


def overhead_breakdown(mode, cond, profile) -> dict:
    """Components of the extra time security adds, in ms:
       compute  = measured median handshake time (key gen + exchange + HKDF)
       transfer = simulated time to send the handshake bytes over the link
       aes      = time to AES-encrypt the payload at the measured throughput
    (Sending the payload itself costs the same in every mode, so it is not counted.)"""
    m = profile["modes"][mode]
    return {"compute": m["handshake_ms_median"],
            "transfer": transfer_ms(m["handshake_bytes"], cond.bandwidth_kbps),
            "aes": max(cond.data_bytes, 0) / (profile["aes"]["mb_per_s"] * 1e6) * 1000}


def overhead_ms(mode, cond, profile) -> float:
    """Extra time the security setup adds: measured crypto time + time to send handshake bytes
       + time to AES-encrypt the payload."""
    return sum(overhead_breakdown(mode, cond, profile).values())
