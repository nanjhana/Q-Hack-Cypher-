"""Adaptive security decision engine (spec Section 12.2).

Pure, deterministic, explainable logic -- no crypto, no ML:

    security_need        = 0.6 x sensitivity_score + 0.4 x lifetime_score
    performance_pressure = 0.65 x latency_pressure + 0.35 x bandwidth_pressure
    net                  = security_need - performance_pressure

    net >= +25 -> QUANTUM_SAFE,  net <= -25 -> CLASSICAL,  otherwise HYBRID
    then: safety floor, then feasibility check using MEASURED benchmark costs.
"""
import json
import os
from dataclasses import dataclass, field
from math import log

from simulation.network import overhead_ms

LEVELS = {"LOW": 10, "MEDIUM": 45, "HIGH": 80, "CRITICAL": 100}
W = {"sens": 0.6, "life": 0.4, "lat": 0.65, "bw": 0.35}
T_HIGH, T_LOW = 25, -25                        # thresholds on net score
FLOOR_LEVELS = ("HIGH", "CRITICAL")
FLOOR_YEARS = 10
PQ_MODES = ("QUANTUM_SAFE", "HYBRID")

PROFILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmarking", "results.json")


@dataclass
class Conditions:
    sensitivity: str            # LOW | MEDIUM | HIGH | CRITICAL
    lifetime_years: float       # how long the data must stay secret
    latency_budget_ms: float    # max extra delay security may add
    bandwidth_kbps: float
    data_bytes: int = 10_000


@dataclass
class Decision:
    mode: str
    need: float
    pressure: float
    net: float
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    estimates_ms: dict = field(default_factory=dict)
    score_mode: str = ""            # mode chosen by the score alone, before guard rails
    floor_applied: bool = False     # safety floor is active for these conditions
    downgraded: bool = False        # feasibility check forced CLASSICAL
    components: dict = field(default_factory=dict)   # normalised 0-100 inputs


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def load_profile(path: str = PROFILE_PATH) -> dict:
    """Load the measured benchmark profile. Run `python -m benchmarking.run_benchmarks` first."""
    with open(path) as f:
        return json.load(f)


def scores(c: Conditions) -> dict:
    """Normalise each input to 0-100 (spec table in Section 12.2)."""
    if c.sensitivity not in LEVELS:
        raise ValueError(f"sensitivity must be one of {list(LEVELS)}, got {c.sensitivity!r}")
    return {
        "sensitivity": float(LEVELS[c.sensitivity]),
        "lifetime": clamp(c.lifetime_years / 15 * 100),                                  # 15+ years = max
        "latency": clamp(100 * log(500 / max(c.latency_budget_ms, 1e-6)) / log(100)),    # <=5 ms -> 100, >=500 ms -> 0
        "bandwidth": clamp(100 * log(100_000 / max(c.bandwidth_kbps, 1e-6)) / log(1000)),  # <=100 kbps -> 100, >=100 Mbps -> 0
    }


def _label(mode: str) -> str:
    return mode.replace("_", "-")


def decide(c: Conditions, profile: dict) -> Decision:
    s = scores(c)
    need = W["sens"] * s["sensitivity"] + W["life"] * s["lifetime"]
    pressure = W["lat"] * s["latency"] + W["bw"] * s["bandwidth"]
    net = need - pressure

    d = Decision("HYBRID", need, pressure, net, components=s)
    d.estimates_ms = {m: overhead_ms(m, c, profile) for m in profile["modes"]}
    d.reasons.append(f"Security need {need:.0f} vs performance pressure {pressure:.0f} (net {net:+.1f}).")

    if net >= T_HIGH:
        d.mode = "QUANTUM_SAFE"; d.reasons.append("Security need clearly exceeds performance pressure.")
    elif net <= T_LOW:
        d.mode = "CLASSICAL"; d.reasons.append("Performance pressure clearly exceeds security need.")
    else:
        d.reasons.append("Security and performance are balanced, so combine both.")
    d.score_mode = d.mode

    floor = c.sensitivity in FLOOR_LEVELS and c.lifetime_years >= FLOOR_YEARS
    d.floor_applied = floor
    if floor and d.mode == "CLASSICAL":
        d.mode = "HYBRID"; d.reasons.append("Safety floor: sensitive, long-lived data is never sent classical-only.")

    if d.mode != "CLASSICAL" and d.estimates_ms[d.mode] > c.latency_budget_ms:
        if floor:
            d.warnings.append(f"{_label(d.mode)} needs ~{d.estimates_ms[d.mode]:.1f} ms but budget is "
                              f"{c.latency_budget_ms:g} ms. Keeping it because of the safety floor; "
                              "consider relaxing the latency budget.")
        else:
            d.reasons.append(f"Feasibility check: {_label(d.mode)} setup would need ~{d.estimates_ms[d.mode]:.1f} ms, "
                             f"exceeding the {c.latency_budget_ms:g} ms latency budget on this link.")
            d.mode = "CLASSICAL"; d.downgraded = True
            d.warnings.append("Downgraded for performance. Re-key with PQC when conditions improve.")
    elif d.mode != "CLASSICAL":
        d.reasons.append(f"Feasibility check passed: {_label(d.mode)} needs ~{d.estimates_ms[d.mode]:.2f} ms "
                         f"(measured), within the {c.latency_budget_ms:g} ms budget.")
    else:
        # CLASSICAL chosen by score: report (informational only) whether PQ modes would even fit.
        too_slow = [m for m in PQ_MODES if m in d.estimates_ms and d.estimates_ms[m] > c.latency_budget_ms]
        if too_slow:
            d.reasons.append("On this link the post-quantum modes would also exceed the budget ("
                             + ", ".join(f"{_label(m)} ~{d.estimates_ms[m]:.1f} ms" for m in too_slow)
                             + f" > {c.latency_budget_ms:g} ms).")
    return d
