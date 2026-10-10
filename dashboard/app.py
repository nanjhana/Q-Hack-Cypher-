"""AdaptiveCrypt -- multi-page adaptive cryptography dashboard.

Run from the project root:   streamlit run dashboard/app.py

REAL:      key establishment (X25519 / ML-KEM-768), AES-256-GCM, timings, byte sizes.
SIMULATED: network bandwidth/latency, the HPC-QC environment, workload scenarios.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import streamlit as st  # noqa: E402

from crypto_suite import pqc  # noqa: E402
from dashboard.shared import fmt_bw, fmt_size  # noqa: E402
from decision_engine.policy import (LEVELS, PROFILE_PATH,  # noqa: E402
                                    Conditions, decide, load_profile)
from simulation.scenarios import SCENARIOS, TIMELINE  # noqa: E402

# ---- Page config ----
st.set_page_config(page_title="AdaptiveCrypt", layout="wide")

# ---- CSS (injected on every page) ----
st.markdown("""
<style>
:root { --sidebar-width: 292px; --header-height: 62px; }

.stApp {font-family: 'Inter', 'SF Pro Display', -apple-system, sans-serif;}

/* --- Fixed Top Navigation Bar --- */
header[data-testid="stHeader"] {
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    width: 100vw !important;
    height: var(--header-height) !important;
    background-color: #121214 !important;
    border-bottom: 1px solid #27272a !important;
    z-index: 999999 !important;
    display: flex !important;
    align-items: center !important;
    padding: 0 !important;
}

div[data-testid="stToolbar"] {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    height: 100% !important;
}

/* Inner flex wrapper (contains logo container + nav overflow) */
div[data-testid="stToolbar"] > div {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    height: 100% !important;
}

/* Logo container -- the first child div inside the toolbar inner wrapper.
   This is the empty div Streamlit renders before the nav links. */
div[data-testid="stToolbar"] > div > div:first-child {
    width: var(--sidebar-width) !important;
    min-width: var(--sidebar-width) !important;
    flex: 0 0 var(--sidebar-width) !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    border-right: 1px solid #27272a !important;
    box-sizing: border-box !important;
    padding-left: 24px !important;
}

/* AdaptiveCrypt text logo -- rendered inside the logo container */
div[data-testid="stToolbar"] > div > div:first-child::before {
    content: "AdaptiveCrypt";
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #f4f4f5;
    white-space: nowrap;
    line-height: 1;
}

/* Remove old toolbar-level pseudo (in case Streamlit still renders it) */
div[data-testid="stToolbar"]::before {
    content: none !important;
    display: none !important;
}

/* Remove old divider -- the logo container's right border replaces it */
.rc-overflow::before {
    content: none !important;
    display: none !important;
}

/* Nav links container -- fills remaining space after logo */
.rc-overflow {
    padding-left: 16px !important;
}

/* Nav links styling */
[data-testid="stTopNavLinkContainer"] {
    margin: 0 2px !important;
}

[data-testid="stTopNavLink"] {
    border-radius: 3px !important;
    padding: 6px 12px !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: #a1a1aa !important;
    text-decoration: none !important;
    transition: all 0.15s ease !important;
    border-bottom: 2px solid transparent !important;
}

[data-testid="stTopNavLink"]:hover {
    color: #f4f4f5 !important;
    background-color: rgba(255, 255, 255, 0.04) !important;
}

[data-testid="stTopNavLink"][aria-current="page"] {
    color: #f4f4f5 !important;
    font-weight: 600 !important;
    background-color: rgba(255, 255, 255, 0.06) !important;
    border-bottom: 2px solid #60a5fa !important;
}

[data-testid="stTopNavLink"] p {
    margin: 0 !important;
    font-size: 0.88rem !important;
    line-height: 1.4 !important;
}

.stAppDeployButton, [data-testid="stHeaderActionElements"] {
    display: none !important;
}

/* --- Conditions Sidebar beneath Top Nav --- */
section[data-testid="stSidebar"] {
    top: var(--header-height) !important;
    height: calc(100vh - var(--header-height)) !important;
    width: var(--sidebar-width) !important;
    min-width: var(--sidebar-width) !important;
    flex: 0 0 var(--sidebar-width) !important;
    background: #18181b !important;
    border-right: 1px solid #27272a !important;
    z-index: 99990 !important;
    box-sizing: border-box !important;
}
section[data-testid="stSidebar"] * {color: #d4d4d8 !important;}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    box-sizing: border-box !important;
    overflow-x: hidden !important;
}

/* --- Page Content container alignment & spacing --- */
[data-testid="stMainBlockContainer"] {
    padding-top: 86px !important;
}

/* --- Responsive: narrower sidebar on small screens --- */
@media (max-width: 768px) {
    :root { --sidebar-width: 220px; }
}

/* --- Components --- */
.mode-badge {border-radius: 3px; padding: 20px 22px; color: #f4f4f5; margin-bottom: 8px;
             border: 1px solid rgba(255,255,255,.08); background: #27272a;}
.mode-badge .k {font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; color: #a1a1aa;}
.mode-badge .m {font-size: 2.2rem; font-weight: 700; line-height: 1.15; margin: 4px 0; color: #f4f4f5;}
.mode-badge .a {font-size: .88rem; font-weight: 500; color: #d4d4d8;}
.mode-badge .ind {display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 8px;
                  vertical-align: middle;}

.tl-card {border-radius: 3px; padding: 12px 14px; border: 1px solid #3f3f46; min-height: 140px;
          background: #1c1c1f;}
.tl-card.active {border-color: #a1a1aa; border-width: 2px; background: #27272a;}
.tl-mode {display: inline-block; border-radius: 2px; padding: 2px 8px; font-weight: 600;
          margin: 4px 0; font-size: .82rem; border: 1px solid #52525b; color: #d4d4d8;}
.tl-cond {font-size: .78rem; color: #71717a;}
.tl-label {font-weight: 600; font-size: .88rem; color: #d4d4d8;}
</style>
""", unsafe_allow_html=True)

# ---- Constants ----
CUSTOM = "Custom"
BW_OPTIONS = [100, 200, 300, 500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]
SIZE_OPTIONS = [100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000]


# ---- Profile loading ----
@st.cache_data(show_spinner=False)
def _load_profile_cached(mtime: float) -> dict:
    return load_profile()


def get_profile():
    if not os.path.exists(PROFILE_PATH):
        return None
    return _load_profile_cached(os.path.getmtime(PROFILE_PATH))


def rerun_benchmark():
    from benchmarking.run_benchmarks import run
    runs = 200 if pqc.HARDENED else 30
    with st.spinner(f"Running benchmark ({runs} handshakes per mode)..."):
        out = run(runs=runs, warmup=10 if pqc.HARDENED else 3)
        with open(PROFILE_PATH, "w") as f:
            json.dump(out, f, indent=2)
    st.session_state.pop("live", None)


profile = get_profile()
if profile is None:
    st.title("AdaptiveCrypt")
    st.warning("No benchmark profile found. Run `python -m benchmarking.run_benchmarks` or click below.")
    if st.button("Run benchmark now", type="primary"):
        rerun_benchmark()
        st.rerun()
    st.stop()


# ---- State & callbacks ----
def apply_scenario(name: str):
    c = SCENARIOS[name]
    st.session_state.update(sens=c.sensitivity, life=float(c.lifetime_years), lat=int(c.latency_budget_ms),
                            bw=int(c.bandwidth_kbps), size=int(c.data_bytes), preset=name, timeline=name)


def on_preset_change():
    if st.session_state.preset != CUSTOM:
        apply_scenario(st.session_state.preset)


def mark_custom():
    st.session_state.preset = CUSTOM


if "sens" not in st.session_state:
    apply_scenario(TIMELINE[0])


# ---- Navigation ----
pg = st.navigation([
    st.Page("pages/decision.py", title="Decision", default=True, url_path="decision"),
    st.Page("pages/performance.py", title="Performance"),
    st.Page("pages/network_cost.py", title="Network Cost"),
    st.Page("pages/handshake.py", title="Handshake Size"),
    st.Page("pages/live_encryption.py", title="Live Encryption"),
    st.Page("pages/adaptive.py", title="Adaptive Switching"),
], position="top")


# ---- Sidebar: Conditions ----
with st.sidebar:
    st.markdown("**CONDITIONS**")
    st.selectbox("Scenario", [CUSTOM] + TIMELINE, key="preset", on_change=on_preset_change)
    st.markdown("")
    st.markdown("**Data**")
    st.select_slider("Sensitivity", list(LEVELS), key="sens", on_change=mark_custom)
    st.slider("Lifetime (years)", 0.0, 30.0, step=0.1, key="life", on_change=mark_custom)
    st.select_slider("Size", SIZE_OPTIONS, key="size", format_func=fmt_size, on_change=mark_custom)
    st.markdown("")
    st.markdown("**Network**")
    st.slider("Latency budget (ms)", 1, 500, key="lat", on_change=mark_custom)
    st.select_slider("Bandwidth", BW_OPTIONS, key="bw", format_func=fmt_bw, on_change=mark_custom)
    st.divider()
    st.markdown("**Benchmark**")
    st.caption(f"{profile['machine']['cpu']}")
    st.caption(f"PQC: {profile['pqc_backend']}")
    if st.button("Re-run benchmark", width="stretch"):
        rerun_benchmark()
        st.rerun()


# ---- Compute decision & store for pages ----
cond = Conditions(st.session_state.sens, st.session_state.life, st.session_state.lat,
                  st.session_state.bw, st.session_state.size)
dec = decide(cond, profile)
st.session_state["app_profile"] = profile
st.session_state["app_decision"] = dec
st.session_state["app_conditions"] = cond


# ---- Run selected page ----
pg.run()
