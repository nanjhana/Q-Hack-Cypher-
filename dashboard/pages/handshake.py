import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import altair as alt
import pandas as pd
import streamlit as st

from crypto_suite.suite import MODES
from dashboard.shared import MODE_ACCENT, label

profile = st.session_state["app_profile"]

st.title("Handshake Size")

bdf = pd.DataFrame([{
    "Mode": label(m),
    "Bytes": profile["modes"][m]["handshake_bytes"],
    "key": m,
} for m in MODES])

st.altair_chart(
    alt.Chart(bdf).mark_bar().encode(
        x=alt.X("Mode:N", sort=[label(m) for m in MODES], title=None),
        y=alt.Y("Bytes:Q", title="Handshake bytes"),
        color=alt.Color("key:N", scale=alt.Scale(
            domain=list(MODE_ACCENT), range=list(MODE_ACCENT.values())), legend=None),
        tooltip=["Mode", "Bytes"],
    ).properties(height=300)
    + alt.Chart(bdf).mark_text(dy=-8, fontWeight="bold", color="#d4d4d8").encode(
        x=alt.X("Mode:N", sort=[label(m) for m in MODES]),
        y="Bytes:Q",
        text="Bytes:Q"),
    width="stretch",
)
