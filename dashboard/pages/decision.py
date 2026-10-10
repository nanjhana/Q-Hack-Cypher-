import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st

from crypto_suite.suite import ALGORITHMS
from dashboard.shared import MODE_ACCENT, label
from decision_engine.policy import FLOOR_YEARS

d = st.session_state["app_decision"]
profile = st.session_state["app_profile"]

st.title("Decision")

scen = st.session_state.preset if st.session_state.preset != "Custom" else "Custom conditions"
st.caption(f"Scenario: {scen}")

accent = MODE_ACCENT[d.mode]
st.markdown(f"""
<div class="mode-badge">
  <div class="k">Selected Security Mode</div>
  <div class="m"><span class="ind" style="background:{accent}"></span>{label(d.mode)}</div>
  <div class="a">{ALGORITHMS[d.mode]}</div>
</div>""", unsafe_allow_html=True)

st.markdown("")
st.markdown("**Decision**")
for r in d.reasons:
    st.markdown(f"- {r}")

for w in d.warnings:
    st.warning(w)

if d.floor_applied:
    st.caption(f"Safety floor active: HIGH/CRITICAL data with lifetime >= {FLOOR_YEARS} years "
               "is never classical-only.")
if d.downgraded:
    st.caption("Mode was downgraded due to feasibility constraints.")

hardened = profile.get("pqc_backend_hardened", True)
if not hardened:
    st.warning("PQC backend is the pure-Python educational fallback (not hardened, not constant-time). "
               "Timings are indicative only.")

st.divider()
st.caption("Prototype for evaluation and education. Not production-ready, not audited. "
           "Quantum-safe = post-quantum cryptography (ML-KEM-768, FIPS 203) on classical hardware.")
