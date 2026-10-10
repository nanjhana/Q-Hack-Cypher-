"""Integration + switching tests: benchmark JSON -> decision -> real roundtrip."""
import json
import os

import pytest

from benchmarking import run_benchmarks
from crypto_suite.suite import MODES, secure_roundtrip
from decision_engine.policy import PROFILE_PATH, decide, load_profile
from simulation.scenarios import EXPECTED, SCENARIOS, TIMELINE
from tests.test_policy import FIXTURE

needs_results = pytest.mark.skipif(not os.path.exists(PROFILE_PATH),
                                   reason="run `python -m benchmarking.run_benchmarks` first")


# ---------------------------------------------------------------- benchmark file
@needs_results
def test_benchmark_file_loads_with_all_fields():
    p = load_profile()
    assert p["pqc_backend"]
    assert set(p["modes"]) == set(MODES)
    for m in MODES:
        r = p["modes"][m]
        for k in ("handshake_ms_median", "handshake_ms_mean", "handshake_ms_p95", "handshake_bytes", "runs"):
            assert r[k] > 0, (m, k)
        assert r["handshake_ms_median"] <= r["handshake_ms_p95"]
    assert p["aes"]["mb_per_s"] > 0


@needs_results
def test_benchmark_bytes_match_real_handshakes():
    p = load_profile()
    for m in MODES:
        assert p["modes"][m]["handshake_bytes"] == secure_roundtrip(m, b"x")["handshake_bytes"]


def test_benchmark_functions_produce_positive_numbers(tmp_path):
    out = tmp_path / "r.json"
    run_benchmarks.main(["--runs", "5", "--warmup", "1", "--aes-runs", "2", "--out", str(out)])
    data = json.loads(out.read_text())
    assert set(data["modes"]) == set(MODES)
    assert all(data["modes"][m]["handshake_ms_median"] > 0 for m in MODES)
    assert data["aes"]["mb_per_s"] > 0 and data["machine"]["python"]


def test_pct_helper():
    assert run_benchmarks.pct(list(range(100)), 0.95) == 95
    assert run_benchmarks.pct([7], 0.95) == 7


# ---------------------------------------------------------------- scenarios / switching
@pytest.mark.parametrize("name", TIMELINE)
def test_scenarios_expected_with_fixture(name):
    assert decide(SCENARIOS[name], FIXTURE).mode == EXPECTED[name]


@needs_results
@pytest.mark.parametrize("name", TIMELINE)
def test_scenarios_with_measured_profile(name):
    d = decide(SCENARIOS[name], load_profile())
    assert d.reasons
    # With real measurements a feasibility downgrade is legitimate, but must be explained.
    if d.mode != EXPECTED[name]:
        assert d.downgraded and d.warnings, f"{name}: unexpected {d.mode} without a downgrade explanation"


def test_timeline_switches_at_least_three_times():
    modes = [decide(SCENARIOS[n], FIXTURE).mode for n in TIMELINE]
    assert len(set(modes)) == 3
    assert sum(a != b for a, b in zip(modes, modes[1:])) >= 3


@needs_results
@pytest.mark.parametrize("name", TIMELINE)
def test_decision_then_real_roundtrip(name):
    c = SCENARIOS[name]
    d = decide(c, load_profile())
    r = secure_roundtrip(d.mode, os.urandom(c.data_bytes))
    assert r["mode"] == d.mode and r["correct"] is True


@pytest.mark.parametrize("mode", MODES)
def test_all_three_modes_work_end_to_end(mode):
    assert secure_roundtrip(mode, b"sample HPC result " * 100)["correct"]
