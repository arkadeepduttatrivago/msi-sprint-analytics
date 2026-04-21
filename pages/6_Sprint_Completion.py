"""Page 6: Sprint Completion — all active sprints with completion rates."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from lib.data_loader import (
    get_snapshot_metrics, get_snapshot_issues, get_sprint_snapshots,
    get_combined_sprint_metrics,
    COMPLETED_STATUSES, NOT_IN_SPRINT_STATUSES,
    TEAM_DISPLAY, ALL_TEAMS, ALL_ASSIGNEES,
)
from lib.brand import (
    section_header, apply_chart_defaults, kpi_row,
    RED, BLUE, ORANGE, LIGHTBLUE, YELLOW, PINK,
    GRAY_100, GRAY_300, GRAY_500, GRAY_700, GRAY_900,
    SERIES_ORDER, FONT_STACK,
)

st.set_page_config(page_title="Sprint Completion", page_icon="📋", layout="wide")

team = st.session_state.get("team", ALL_TEAMS)
assignee = st.session_state.get("assignee", ALL_ASSIGNEES)
team_label = TEAM_DISPLAY.get(team, team) if team != ALL_TEAMS else ""
title_suffix = f" — {team_label}" if team_label else ""
st.markdown(f"## 📋 Current Sprint Completion{title_suffix}")
st.caption(
    "**Committed SP** = total story points of all in-sprint tickets. "
    "**Completed SP** = story points of tickets in Feedback/Done. "
    "**Carry-Over** = committed minus completed."
)

active_sprints = get_sprint_snapshots()
if not active_sprints:
    st.warning("No active sprints. Run `/update-sprint-analytics` to fetch data.")
    st.stop()

# ── Per-Sprint Completion Cards ──────────────────────────────────────
section_header("Sprint Completion Overview")

sprint_colors = [RED, BLUE, ORANGE, LIGHTBLUE, PINK, YELLOW]
sprint_data: list[dict] = []

for sp_name in active_sprints:
    m = get_snapshot_metrics(sp_name, team)
    if not m:
        sprint_data.append({
            "sprint_name": sp_name,
            "committed_sp": 0, "completed_sp": 0,
            "commitment_ratio": 0, "carry_over_sp": 0,
        })
        continue
    sprint_data.append({
        "sprint_name": sp_name,
        "committed_sp": m.get("committed_sp", 0),
        "completed_sp": m.get("completed_sp", 0),
        "commitment_ratio": m.get("commitment_ratio", 0),
        "carry_over_sp": m.get("carry_over_sp", 0),
    })

cols = st.columns(len(sprint_data))
for i, sp in enumerate(sprint_data):
    color = sprint_colors[i % len(sprint_colors)]
    ratio = sp["commitment_ratio"]
    ratio_color = BLUE if ratio >= 0.8 else (ORANGE if ratio >= 0.5 else RED)
    pct = int(ratio * 100)
    with cols[i]:
        st.markdown(
            f'<div style="background:{GRAY_100};border-radius:12px;padding:18px 14px;'
            f'border-top:4px solid {color};">'
            f'<div style="font-size:13px;font-weight:700;color:{GRAY_700};'
            f'margin-bottom:10px;text-align:center;">{sp["sprint_name"]}</div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="font-size:11px;color:{GRAY_500};">Committed</span>'
            f'<span style="font-size:14px;font-weight:700;color:{GRAY_900};">'
            f'{sp["committed_sp"]:.1f} SP</span></div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="font-size:11px;color:{GRAY_500};">Completed</span>'
            f'<span style="font-size:14px;font-weight:700;color:{color};">'
            f'{sp["completed_sp"]:.1f} SP</span></div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
            f'<span style="font-size:11px;color:{GRAY_500};">Carry-Over</span>'
            f'<span style="font-size:14px;font-weight:700;color:{ORANGE};">'
            f'{sp["carry_over_sp"]:.1f} SP</span></div>'
            # Progress bar
            f'<div style="background:{GRAY_300};border-radius:6px;height:18px;'
            f'overflow:hidden;position:relative;">'
            f'<div style="background:{ratio_color};height:100%;width:{min(pct, 100)}%;'
            f'border-radius:6px;transition:width .3s;"></div>'
            f'<div style="position:absolute;top:0;left:0;right:0;text-align:center;'
            f'font-size:11px;font-weight:700;color:{GRAY_900};line-height:18px;">'
            f'{ratio:.0%}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Total across all sprints ────────────────────────────────────────
combined = get_combined_sprint_metrics(team)
total_ratio = combined.get("commitment_ratio", 0)
st.markdown("")
kpi_row([
    {"label": "Total Committed SP", "value": f"{combined['committed_sp']:.1f}", "color": BLUE},
    {"label": "Total Completed SP", "value": f"{combined['completed_sp']:.1f}", "color": LIGHTBLUE},
    {"label": "Overall Completion", "value": f"{total_ratio:.0%}",
     "color": BLUE if total_ratio >= 0.8 else RED},
    {"label": "Total Carry-Over", "value": f"{combined['carry_over_sp']:.1f}", "color": ORANGE},
])

# ── Completion Rate Comparison Chart ─────────────────────────────────
st.divider()
section_header("Completion Rate Comparison")

sp_names = [sp["sprint_name"] for sp in sprint_data]
sp_ratios = [sp["commitment_ratio"] * 100 for sp in sprint_data]
bar_colors = [
    BLUE if r >= 80 else (ORANGE if r >= 50 else RED) for r in sp_ratios
]

fig_rate = go.Figure()
fig_rate.add_trace(go.Bar(
    x=sp_names, y=sp_ratios,
    marker_color=bar_colors,
    text=[f"{r:.0f}%" for r in sp_ratios],
    textposition="outside",
    textfont=dict(size=14, color=GRAY_900),
))
fig_rate.add_hline(y=80, line_dash="dash", line_color=GRAY_500,
                   annotation_text="80% target", annotation_position="top right")
fig_rate.update_layout(
    yaxis_title="Completion %", yaxis=dict(range=[0, max(110, max(sp_ratios) + 15)]),
    showlegend=False,
)
st.plotly_chart(apply_chart_defaults(fig_rate, height=350), width="stretch")

# ── Committed vs Completed bars ──────────────────────────────────────
st.divider()
section_header("Committed vs Completed by Sprint")

fig_bars = go.Figure()
fig_bars.add_trace(go.Bar(
    x=sp_names, y=[sp["committed_sp"] for sp in sprint_data],
    name="Committed SP", marker_color=BLUE,
    text=[f"{sp['committed_sp']:.1f}" for sp in sprint_data], textposition="outside",
))
fig_bars.add_trace(go.Bar(
    x=sp_names, y=[sp["completed_sp"] for sp in sprint_data],
    name="Completed SP", marker_color=LIGHTBLUE,
    text=[f"{sp['completed_sp']:.1f}" for sp in sprint_data], textposition="outside",
))
fig_bars.update_layout(
    barmode="group", yaxis_title="Story Points",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(apply_chart_defaults(fig_bars, height=380), width="stretch")

# ── In-Progress Tickets per Sprint ───────────────────────────────────
st.divider()
section_header("In-Progress Tickets (Not Yet Completed)")

for sp_name in active_sprints:
    df = get_snapshot_issues(sp_name, team, assignee)
    if df.empty:
        continue
    mask = df["status"].apply(
        lambda s: s not in NOT_IN_SPRINT_STATUSES and s not in COMPLETED_STATUSES
    )
    in_progress = df[mask]
    with st.expander(f"**{sp_name}** — {len(in_progress)} in-progress tickets"):
        if in_progress.empty:
            st.success("All committed tickets are completed.")
        else:
            display_cols = [c for c in ["key", "summary", "assignee", "status",
                                         "story_points", "team"] if c in in_progress.columns]
            st.dataframe(in_progress[display_cols], width="stretch", hide_index=True)
