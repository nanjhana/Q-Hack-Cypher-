"""Decision-engine unit tests. They use a FIXTURE profile so they never depend on this laptop's speed."""
import math

import pytest

from decision_engine.policy import LEVELS, T_HIGH, T_LOW, Conditions, decide, scores

FIXTURE = {  # test fixture, NOT a benchmark
    "modes": {"CLASSICAL": {"handshake_ms_median": 0.1, "handshake_bytes": 64},
              "QUANTUM_SAFE": {"handshake_ms_median": 0.2, "handshake_bytes": 2272},
              "HYBRID": {"handshake_ms_median": 0.3, "handshake_bytes": 2336}},
    "aes": {"mb_per_s": 1000}}

SLOW_FIXTURE = {  # test fixture, NOT a benchmark: pretend PQC compute is very slow
    "modes": {"CLASSICAL": {"handshake_ms_median": 0.1, "handshake_bytes": 64},
              "QUANTUM_SAFE": {"handshake_ms_median": 80.0, "handshake_bytes": 2272},
              "HYBRID": {"handshake_ms_median": 90.0, "handshake_bytes": 2336}},
    "aes": {"mb_per_s": 1000}}


# ---------------------------------------------------------------- spec test matrix (Section 16)
def test_speed_priority():
    d = decide(Conditions("LOW", 0.1, 10, 10_000), FIXTURE)
    assert d.mode == "CLASSICAL"
    assert "Performance pressure clearly exceeds security need." in d.reasons


def test_max_security():
    d = decide(Conditions("CRITICAL", 25, 200, 100_000), FIXTURE)
    assert d.mode == "QUANTUM_SAFE"
    assert "Security need clearly exceeds performance pressure." in d.reasons


def test_balanced():
    d = decide(Conditions("MEDIUM", 5, 50, 20_000), FIXTURE)
    assert d.mode == "HYBRID"
    assert T_LOW < d.net < T_HIGH


def test_constrained():
    assert decide(Conditions("MEDIUM", 5, 20, 300), FIXTURE).mode == "CLASSICAL"


def test_safety_floor():
    d = decide(Conditions("HIGH", 15, 5, 100), FIXTURE)
    assert d.mode != "CLASSICAL" and d.warnings
    assert d.floor_applied


def test_lowest_bandwidth_no_crash():
    d = decide(Conditions("MEDIUM", 1, 100, 100), FIXTURE)
    assert d.mode in FIXTURE["modes"] and d.reasons


def test_zero_lifetime():
    # NOTE: the spec's test matrix lists CLASSICAL here, but the spec's own formula gives
    # need = 0.6*10 + 0 = 6, pressure = 0 (500 ms budget, 100 Mbps) -> net = +6 -> HYBRID.
    # We follow the documented formula (no pressure means PQ protection is essentially free).
    d = decide(Conditions("LOW", 0, 500, 100_000), FIXTURE)
    assert math.isclose(d.net, 6.0, abs_tol=1e-9)
    assert d.mode == "HYBRID"
    assert not d.warnings


# ---------------------------------------------------------------- hand-checked scores (Section 12.3)
@pytest.mark.parametrize("cond, need, pressure, net", [
    (Conditions("LOW", 0.1, 10, 10_000), 6, 67, -60),
    (Conditions("CRITICAL", 25, 200, 100_000), 100, 13, 87),
    (Conditions("MEDIUM", 5, 50, 20_000), 40, 41, -0.4),
    (Conditions("MEDIUM", 5, 20, 300), 40, 75, -35),
])
def test_hand_checked_scores(cond, need, pressure, net):
    d = decide(cond, FIXTURE)
    assert abs(d.need - need) < 1 and abs(d.pressure - pressure) < 1 and abs(d.net - net) < 1


def test_score_mappings_endpoints():
    s = scores(Conditions("CRITICAL", 15, 5, 100))
    assert s == {"sensitivity": 100, "lifetime": 100, "latency": 100, "bandwidth": 100}
    s = scores(Conditions("LOW", 0, 500, 100_000))
    assert s["latency"] == 0 and s["bandwidth"] == 0 and s["lifetime"] == 0 and s["sensitivity"] == LEVELS["LOW"]


# ---------------------------------------------------------------- guard rails
def test_feasibility_downgrade_has_reason_and_warning():
    # Balanced by score (net ~ -22) but HYBRID handshake bytes take ~62 ms at 300 kbps > 50 ms.
    d = decide(Conditions("MEDIUM", 5, 50, 300), FIXTURE)
    assert d.score_mode == "HYBRID" and d.mode == "CLASSICAL" and d.downgraded
    assert any("Feasibility check" in r for r in d.reasons)
    assert any("Downgraded for performance" in w for w in d.warnings)


def test_feasibility_uses_measured_compute_time():
    # Same conditions as max security, but a (fake) very slow PQC profile breaks a 50 ms budget.
    d = decide(Conditions("CRITICAL", 5, 50, 100_000), SLOW_FIXTURE)
    assert d.score_mode == "QUANTUM_SAFE" and d.mode == "CLASSICAL" and d.downgraded


def test_floor_keeps_pq_mode_even_if_infeasible():
    d = decide(Conditions("CRITICAL", 20, 20, 300), FIXTURE)
    assert d.mode in ("QUANTUM_SAFE", "HYBRID") and not d.downgraded
    assert any("safety floor" in w for w in d.warnings)


def test_floor_not_applied_below_10_years():
    d = decide(Conditions("HIGH", 9.9, 5, 100), FIXTURE)
    assert not d.floor_applied and d.mode == "CLASSICAL"


@pytest.mark.parametrize("sens", list(LEVELS))
@pytest.mark.parametrize("lat", [0, 1, 5, 500, 10_000])
@pytest.mark.parametrize("bw", [0, 1, 100, 100_000, 10_000_000])
@pytest.mark.parametrize("life", [0, 10, 1000, -5])
def test_extreme_values_never_crash(sens, lat, bw, life):
    d = decide(Conditions(sens, life, lat, bw, 0), FIXTURE)
    assert d.mode in FIXTURE["modes"]
    assert 0 <= d.need <= 100 and 0 <= d.pressure <= 100
    assert d.reasons, "every decision must explain itself"
    if sens in ("HIGH", "CRITICAL") and life >= 10:
        assert d.mode != "CLASSICAL"


def test_every_decision_has_estimates_for_all_modes():
    d = decide(Conditions("MEDIUM", 5, 50, 20_000), FIXTURE)
    assert set(d.estimates_ms) == set(FIXTURE["modes"])
    assert d.estimates_ms["CLASSICAL"] < d.estimates_ms["QUANTUM_SAFE"] < d.estimates_ms["HYBRID"]


def test_invalid_sensitivity_rejected():
    with pytest.raises(ValueError):
        decide(Conditions("ULTRA", 1, 10, 100), FIXTURE)


def test_deterministic():
    c = Conditions("HIGH", 7, 30, 2_000)
    assert decide(c, FIXTURE) == decide(c, FIXTURE)
