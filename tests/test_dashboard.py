"""Headless dashboard tests for the multi-page AdaptiveCrypt application."""
import os

import pytest

from decision_engine.policy import PROFILE_PATH, decide, load_profile
from simulation.scenarios import SCENARIOS, TIMELINE

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboard", "app.py")
pytestmark = pytest.mark.skipif(not os.path.exists(PROFILE_PATH), reason="needs benchmarking/results.json")


def _app():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def _badge_text(at):
    return " ".join(m.value for m in at.markdown if "mode-badge" in m.value)


def _button(at, starts_with):
    return next(b for b in at.button if b.label.startswith(starts_with))


# ---- Default page (Decision) ----

def test_dashboard_loads():
    at = _app()
    assert at.title[0].value == "Decision"
    assert "mode-badge" in _badge_text(at)


@pytest.mark.parametrize("name", TIMELINE)
def test_scenario_dropdown_changes_decision(name):
    at = _app()
    at.selectbox[0].set_value(name).run()
    assert not at.exception
    expected = decide(SCENARIOS[name], load_profile()).mode.replace("_", "-")
    assert expected in _badge_text(at)
    assert at.selectbox[0].value == name


def test_slider_change_marks_custom_and_updates_decision():
    at = _app()
    at.selectbox[0].set_value("3. Balanced workload").run()
    assert "HYBRID" in _badge_text(at)
    at.select_slider(key="bw").set_value(300).run()
    assert not at.exception
    assert "CLASSICAL" in _badge_text(at)
    assert at.selectbox[0].value == "Custom"
    assert any("Downgraded for performance" in w.value for w in at.warning)


# ---- Live Encryption page ----

@pytest.mark.parametrize("name", TIMELINE[:3])
def test_live_encryption_in_selected_mode(name):
    at = _app()
    at.selectbox[0].set_value(name).run()
    at.switch_page("pages/live_encryption.py").run()
    assert not at.exception
    _button(at, "Run real encryption in selected mode").click().run()
    assert not at.exception
    assert any("Decrypted correctly: True" in s.value for s in at.success)


def test_run_all_three_modes():
    at = _app()
    at.switch_page("pages/live_encryption.py").run()
    assert not at.exception
    _button(at, "Run all three modes").click().run()
    assert not at.exception
    assert any("Decrypted correctly: True" in s.value for s in at.success)


# ---- All pages load ----

@pytest.mark.parametrize("page", [
    "pages/performance.py", "pages/network_cost.py", "pages/handshake.py",
    "pages/live_encryption.py", "pages/adaptive.py",
])
def test_page_loads(page):
    at = _app()
    at.switch_page(page).run()
    assert not at.exception, f"Error loading {page}: {at.exception}"
