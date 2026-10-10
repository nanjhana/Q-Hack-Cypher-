import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import streamlit as st

from crypto_suite.suite import MODES
from dashboard.shared import fmt_bw, fmt_size, label
from simulation.network import overhead_breakdown

d = st.session_state["app_decision"]
c = st.session_state["app_conditions"]
profile = st.session_state["app_profile"]

st.title("Network Cost")
st.caption(f"Simulated link: {fmt_bw(c.bandwidth_kbps)} bandwidth, {c.latency_budget_ms:g} ms budget")

rows = []
for m in MODES:
    br = overhead_breakdown(m, c, profile)
    total = d.estimates_ms[m]
    fits = total <= c.latency_budget_ms
    rows.append({
        "Mode": label(m),
        "Crypto compute (ms)": br["compute"],
        "Link transfer (ms)": br["transfer"],
        f"AES {fmt_size(c.data_bytes)} (ms)": br["aes"],
        "Total overhead (ms)": total,
        f"Within {c.latency_budget_ms:g} ms budget": "Yes" if fits else "No",
    })

df = pd.DataFrame(rows)
fmt = {col: "{:.3f}" for col in df.columns if "(ms" in col}
st.dataframe(df.style.format(fmt), hide_index=True)
