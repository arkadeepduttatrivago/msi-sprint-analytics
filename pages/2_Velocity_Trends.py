"""Page 2: Velocity Trends — velocity across sprints with rolling average."""

import streamlit as st
import plotly.graph_objects as go

from lib.data_loader import get_all_snapshots_metrics, TEAM_DISPLAY, ALL_TEAMS
from lib.brand import (
    kpi_row, section_header, apply_chart_defaults,
    RED, BLUE, ORANGE, LIGHTBLUE, GRAY_300,
)

st.set_page_config(page_title="Velocity Trends", page_icon="📈", layout="wide")

team = st.session_state.get("team", ALL_TEAMS)
team_label = TEAM_DISPLAY.get(team, team) if team != ALL_TEAMS else ""
title_suffix = f" — {team_label}" if team_label else ""
st.markdown(f"## 📈 Velocity Trends{title_suffix}")

vt = get_all_snapshots_metrics(team)
if vt.empty or "velocity" not in vt.columns:
    st.info("Not enough sprint data for velocity trends. Run more sprints first.")
    st.stop()

avg_vel = vt["velocity"].mean()
latest_vel = vt["velocity"].iloc[-1]
kpi_row([
    {"label": "Avg Velocity (SP)", "value": f"{avg_vel:.0f}", "color": BLUE},
    {"label": "Latest Sprint", "value": f"{latest_vel:.0f}", "color": ORANGE},
    {
        "label": "Trend",
        "value": "↑" if latest_vel >= avg_vel else "↓",
        "delta": f"vs avg {avg_vel:.0f}",
        "color": BLUE if latest_vel >= avg_vel else RED,
    },
])

st.divider()

section_header("Committed vs Completed per Sprint")

fig = go.Figure()
fig.add_trace(go.Bar(
    x=vt["sprint_name"], y=vt["committed_sp"],
    name="Committed SP", marker_color=BLUE,
    text=vt["committed_sp"].apply(lambda v: f"{v:.0f}"), textposition="outside",
))
fig.add_trace(go.Bar(
    x=vt["sprint_name"], y=vt["completed_sp"],
    name="Completed SP", marker_color=LIGHTBLUE,
    text=vt["completed_sp"].apply(lambda v: f"{v:.0f}"), textposition="outside",
))
if "rolling_avg" in vt.columns:
    fig.add_trace(go.Scatter(
        x=vt["sprint_name"], y=vt["rolling_avg"],
        name="3-Sprint Rolling Avg", mode="lines+markers",
        line=dict(color=ORANGE, width=3), marker=dict(size=6),
    ))
fig.update_layout(
    yaxis_title="Story Points", barmode="group",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(apply_chart_defaults(fig, height=440), width="stretch")

with st.expander("📋 Raw Velocity Data"):
    display_cols = [c for c in ["sprint_name", "committed_sp", "completed_sp",
                                 "velocity", "commitment_ratio", "carry_over_sp",
                                 "rolling_avg"] if c in vt.columns]
    st.dataframe(vt[display_cols], width="stretch", hide_index=True)
