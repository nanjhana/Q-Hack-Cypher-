import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import streamlit as st

from crypto_suite.suite import ALGORITHMS, MODES
from dashboard.shared import label

d = st.session_state["app_decision"]
profile = st.session_state["app_profile"]

st.title("Performance Comparison")

rows = []
for m in MODES:
    pm = profile["modes"][m]
    rows.append({
        "Mode": (">> " if m == d.mode else "") + label(m),
        "Algorithms": ALGORITHMS[m],
        "Handshake median (ms)": pm["handshake_ms_median"],
        "Mean (ms)": pm["handshake_ms_mean"],
        "P95 (ms)": pm["handshake_ms_p95"],
        "Handshake bytes": pm["handshake_bytes"],
    })

df = pd.DataFrame(rows)
fmt = {col: "{:.3f}" for col in df.columns if "(ms" in col}
st.dataframe(df.style.format(fmt | {"Handshake bytes": "{:,}"}), hide_index=True)
