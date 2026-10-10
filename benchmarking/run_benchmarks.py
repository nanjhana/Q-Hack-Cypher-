"""Real performance benchmark for the three security modes.

Run from the project root:

    python -m benchmarking.run_benchmarks            # default: 200 runs, 10 warm-up
    python -m benchmarking.run_benchmarks --runs 30  # quicker (e.g. with the slow kyber-py fallback)

Writes `benchmarking/results.json`. Every number comes from executing real crypto on
this machine with `time.perf_counter()`. Do not hand-edit the output file.
"""
import argparse
import datetime as _dt
import json
import os
import platform
import statistics
import subprocess
import sys
import time

from crypto_suite import pqc
from crypto_suite.common import decrypt, encrypt
from crypto_suite.suite import ALGORITHMS, MODES, establish

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")


def pct(values, p):
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p))]


def bench_mode(mode, runs=200, warmup=10):
    for _ in range(warmup):
        establish(mode)                                     # warm-up, not recorded
    times, wire = [], 0
    for _ in range(runs):
        _, wire, ms = establish(mode)
        times.append(ms)
    return {"algorithms": ALGORITHMS[mode],
            "handshake_ms_median": statistics.median(times),
            "handshake_ms_mean": statistics.mean(times),
            "handshake_ms_p95": pct(times, 0.95),
            "handshake_ms_min": min(times),
            "handshake_ms_max": max(times),
            "handshake_bytes": wire,
            "runs": runs, "warmup": warmup}


def bench_aes(size=1_000_000, runs=20, warmup=3):
    key, data = os.urandom(32), os.urandom(size)
    blob = encrypt(key, data)
    for _ in range(warmup):
        encrypt(key, data)
    enc, dec = [], []
    for _ in range(runs):
        t0 = time.perf_counter(); blob = encrypt(key, data); enc.append(time.perf_counter() - t0)
        t0 = time.perf_counter(); decrypt(key, blob);        dec.append(time.perf_counter() - t0)
    return {"algorithm": "AES-256-GCM",
            "mb_per_s": (size / 1e6) / statistics.median(enc),
            "decrypt_mb_per_s": (size / 1e6) / statistics.median(dec),
            "payload_bytes": size, "ciphertext_overhead_bytes": len(blob) - size, "runs": runs}


def machine_info():
    cpu = platform.processor() or platform.machine()
    if sys.platform == "darwin":
        try:
            cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                 capture_output=True, text=True, timeout=2).stdout.strip() or cpu
        except Exception:
            pass
    return {"cpu": cpu, "machine": platform.machine(), "os": platform.platform(),
            "python": platform.python_version()}


def run(runs=200, warmup=10, aes_runs=20):
    return {"generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "note": "Real local measurements produced by benchmarking/run_benchmarks.py. Do not hand-edit.",
            "pqc_backend": pqc.BACKEND,
            "pqc_backend_hardened": pqc.HARDENED,
            "machine": machine_info(),
            "modes": {m: bench_mode(m, runs, warmup) for m in MODES},
            "aes": bench_aes(runs=aes_runs)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=200, help="measured handshakes per mode (default 200)")
    ap.add_argument("--warmup", type=int, default=10, help="unrecorded warm-up handshakes (default 10)")
    ap.add_argument("--aes-runs", type=int, default=20, help="AES 1 MB encrypt/decrypt runs (default 20)")
    ap.add_argument("--out", default=RESULTS_PATH, help="output JSON path")
    a = ap.parse_args(argv)
    print(f"PQC backend: {pqc.BACKEND}  |  runs={a.runs} warmup={a.warmup}", file=sys.stderr)
    out = run(a.runs, a.warmup, a.aes_runs)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    print(f"\nSaved to {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
