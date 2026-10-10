import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.shared import MODE_ACCENT, fmt_bw, label
from decision_engine.policy import decide
from simulation.scenarios import EXPECTED, SCENARIOS, TIMELINE

profile = st.session_state["app_profile"]
SHORT = {n: n.split(". ", 1)[1].replace(" (after #3)", "") for n in TIMELINE}


def _apply(name: str):
    c = SCENARIOS[name]
    st.session_state.update(sens=c.sensitivity, life=float(c.lifetime_years), lat=int(c.latency_budget_ms),
                            bw=int(c.bandwidth_kbps), size=int(c.data_bytes), preset=name, timeline=name)


def _on_timeline():
    _apply(st.session_state.timeline)


def _next():
    cur = st.session_state.get("timeline", TIMELINE[0])
    _apply(TIMELINE[(TIMELINE.index(cur) + 1) % len(TIMELINE)])


st.title("Adaptive Switching")

if st.session_state.get("timeline") not in TIMELINE:
    st.session_state.timeline = TIMELINE[0]

st.select_slider("Timeline", TIMELINE, key="timeline", on_change=_on_timeline,
                 format_func=lambda n: SHORT[n])

cols = st.columns([1, 1, 1, 1, 0.8])
for col, name in zip(cols, TIMELINE):
    active = st.session_state.preset == name
    col.button(SHORT[name], key=f"tl_{name}", on_click=_apply, args=(name,),
               type="primary" if active else "secondary", width="stretch")
cols[4].button("Next", key="tl_next", on_click=_next, width="stretch")

st.write("")

tl = [(n, decide(SCENARIOS[n], profile)) for n in TIMELINE]
cards = st.columns(len(TIMELINE))
for col, (n, dd), prev in zip(cards, tl, [None] + [x[1] for x in tl[:-1]]):
    sc = SCENARIOS[n]
    active = n == st.session_state.timeline and st.session_state.preset == n
    switch = (f"from {label(prev.mode)}" if prev and prev.mode != dd.mode
              else ("start" if not prev else "unchanged"))
    col.markdown(f"""
    <div class="tl-card {'active' if active else ''}">
      <div class="tl-label">{'> ' if active else ''}{n.replace(' (after #3)', '')}</div>
      <span class="tl-mode">{label(dd.mode)}</span>
      <span class="tl-cond"> {switch}</span>
      <div class="tl-cond">{sc.sensitivity} | {sc.lifetime_years:g}y | {sc.latency_budget_ms:g}ms |
      {fmt_bw(sc.bandwidth_kbps)}<br>net {dd.net:+.1f}</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)

order = ["CLASSICAL", "HYBRID", "QUANTUM_SAFE"]
tdf = pd.DataFrame([{
    "step": i + 1, "Scenario": SHORT[n], "mode": dd.mode,
    "Mode": label(dd.mode), "level": order.index(dd.mode),
    "net": round(dd.net, 1),
} for i, (n, dd) in enumerate(tl)])

line_chart = alt.Chart(tdf).mark_line(
    interpolate="step-after", color="#52525b", strokeWidth=2,
).encode(
    x=alt.X("step:O", title="Timeline step", axis=alt.Axis(labelAngle=0)),
    y=alt.Y("level:Q", scale=alt.Scale(domain=[-0.5, 2.7]), title=None,
            axis=alt.Axis(values=[0, 1, 2],
                          labelExpr="['CLASSICAL','HYBRID','QUANTUM-SAFE'][datum.value]")))
pts = alt.Chart(tdf).mark_circle(size=360, opacity=1).encode(
    x="step:O", y="level:Q",
    color=alt.Color("mode:N", scale=alt.Scale(
        domain=list(MODE_ACCENT), range=list(MODE_ACCENT.values())), legend=None),
    tooltip=["Scenario", "Mode", "net"])
lbl = alt.Chart(tdf).mark_text(dy=-22, fontWeight="bold", color="#a1a1aa").encode(
    x="step:O", y="level:Q", text="Scenario:N")
st.altair_chart(
    (line_chart + pts + lbl).properties(
        height=280,
        padding={"top": 16, "bottom": 20, "left": 8, "right": 8},
    ).configure_view(strokeWidth=0),
    use_container_width=True,
)

mismatch = [n for n, dd in tl if dd.mode != EXPECTED[n]]
if mismatch:
    st.caption("With this machine's measured costs, these steps differ from spec: "
               + ", ".join(f"{SHORT[n]} -> {label(dict(tl)[n].mode)}" for n in mismatch))
