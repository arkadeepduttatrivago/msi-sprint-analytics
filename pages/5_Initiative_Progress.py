"""Page 5: Initiative Progress — weighted KR completion from subtask progress."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from lib.data_loader import get_epic_progress, TEAM_DISPLAY, ALL_TEAMS
from lib.brand import (
    section_header, apply_chart_defaults,
    GRAY_300, GRAY_900, TEAM_COLORS, BLUE, ORANGE, LIGHTBLUE,
)

st.set_page_config(page_title="Initiative Progress", page_icon="🏔️", layout="wide")

team = st.session_state.get("team", ALL_TEAMS)
team_label = TEAM_DISPLAY.get(team, team) if team != ALL_TEAMS else ""
title_suffix = f" — {team_label}" if team_label else ""
st.markdown(f"## 🏔️ Initiative Progress{title_suffix}")
st.caption(
    "**KR Completion** = weighted average of milestone completions. "
    "Each milestone's progress = completed subtasks / total subtasks. "
    "Weights from the planning sheet; equal weights when not specified."
)

prog_df = get_epic_progress(team)
if prog_df.empty:
    st.info("No initiative data for this selection. Run `/update-sprint-analytics` first.")
    st.stop()

section_header("Overall Initiative Completion")

prog_df = prog_df.sort_values("progress", ascending=True)

short_names = [
    f"{r['epic_key']}: {r['summary'][:50]}…" if len(str(r["summary"])) > 50
    else f"{r['epic_key']}: {r['summary']}"
    for _, r in prog_df.iterrows()
]
colors = [TEAM_COLORS.get(r["team"], GRAY_300) for _, r in prog_df.iterrows()]

fig = go.Figure()
fig.add_trace(go.Bar(
    y=short_names,
    x=[p * 100 for p in prog_df["progress"]],
    orientation="h",
    marker_color=colors,
    text=[f"{p:.0%}" for p in prog_df["progress"]],
    textposition="outside",
    textfont_size=11,
))
fig.update_layout(
    xaxis_title="% KR Completion (Weighted)",
    xaxis=dict(range=[0, 110]),
    yaxis=dict(autorange="reversed"),
    margin=dict(l=350),
)
st.plotly_chart(
    apply_chart_defaults(fig, height=max(400, len(prog_df) * 45)),
    width="stretch",
)

display_colors = {TEAM_DISPLAY.get(t, t): c for t, c in TEAM_COLORS.items()}
legend_html = " &nbsp; ".join(
    f'<span style="display:inline-block;width:12px;height:12px;'
    f'background:{c};border-radius:3px;margin-right:4px;'
    f'vertical-align:middle;"></span>'
    f'<span style="font-size:12px;color:{GRAY_900};vertical-align:middle;">{t}</span>'
    for t, c in display_colors.items()
)
st.markdown(legend_html, unsafe_allow_html=True)

st.divider()
section_header("Milestone Detail per Initiative")

options = prog_df["epic_key"].tolist()
selected = st.selectbox(
    "Select an initiative",
    options,
    format_func=lambda k: f"{k}: {prog_df[prog_df['epic_key'] == k]['summary'].iloc[0][:70]}",
)

row = prog_df[prog_df["epic_key"] == selected].iloc[0]
milestones = row.get("milestones", [])
if not milestones:
    st.caption("No milestones found.")
else:
    ms_df = pd.DataFrame(milestones)
    display_cols = [c for c in [
        "key", "summary", "status", "weight",
        "total_subtasks", "done_subtasks", "milestone_progress",
        "story_points", "due_date",
    ] if c in ms_df.columns]
    ms_df_display = ms_df[display_cols].copy()
    if "weight" in ms_df_display.columns:
        ms_df_display["weight"] = ms_df_display["weight"].apply(
            lambda w: f"{w:.0%}" if w is not None else "—"
        )
    if "milestone_progress" in ms_df_display.columns:
        ms_df_display["milestone_progress"] = ms_df_display["milestone_progress"].apply(
            lambda p: f"{p:.0%}"
        )
    ms_df_display.columns = [
        c.replace("_", " ").title() for c in ms_df_display.columns
    ]
    st.dataframe(ms_df_display, width="stretch", hide_index=True)
