import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import streamlit as st

from crypto_suite.suite import MODES, secure_roundtrip
from dashboard.shared import fmt_size, label

d = st.session_state["app_decision"]
c = st.session_state["app_conditions"]

st.title("Live Encryption")
st.caption(f"Selected mode: {label(d.mode)} | Payload: {fmt_size(c.data_bytes)}")

payload = (b"sample HPC result " * (c.data_bytes // 18 + 1))[:c.data_bytes]

b1, b2, _ = st.columns([1.4, 1, 1.2])
if b1.button(f"Run real encryption in selected mode ({label(d.mode)})", type="primary", width="stretch"):
    st.session_state.live = [secure_roundtrip(d.mode, payload)]
if b2.button("Run all three modes", width="stretch"):
    st.session_state.live = [secure_roundtrip(m, payload) for m in MODES]

live = st.session_state.get("live")
if live:
    if len(live) == 1:
        r = live[0]
        ok = r["correct"]
        (st.success if ok else st.error)(
            f"**Decrypted correctly: {ok}** -- {label(r['mode'])} ({r['algorithms']})")
        if r["mode"] != d.mode:
            st.caption(f"Result from earlier run in {label(r['mode'])} mode. "
                       f"Current selection is {label(d.mode)}.")
    else:
        st.success(f"**Decrypted correctly: {all(r['correct'] for r in live)}** for all three modes "
                   f"({fmt_size(len(payload))} payload)")
        st.dataframe(pd.DataFrame([{
            "Mode": label(r["mode"]), "Algorithms": r["algorithms"],
            "Handshake (ms)": round(r["handshake_ms"], 3),
            "Handshake bytes": r["handshake_bytes"],
            "Ciphertext bytes": r["ciphertext_bytes"],
            "Encrypt (ms)": round(r["encrypt_ms"], 3),
            "Decrypt (ms)": round(r["decrypt_ms"], 3),
            "Correct": r["correct"],
        } for r in live]), hide_index=True)
