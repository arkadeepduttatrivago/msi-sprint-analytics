"""Page 1: Sprint Overview — cross-sprint KPIs, per-sprint cards, detail view."""

import streamlit as st
import plotly.graph_objects as go

from lib.data_loader import (
    get_snapshot_metrics, get_snapshot_issues, get_sprint_snapshots,
    get_combined_sprint_metrics,
    TEAM_DISPLAY, ALL_TEAMS, ALL_ASSIGNEES, NOT_IN_SPRINT_STATUSES,
)
from lib.brand import (
    kpi_row, section_header, apply_chart_defaults,
    RED, BLUE, ORANGE, LIGHTBLUE, GRAY_100, GRAY_300, GRAY_500, GRAY_700, GRAY_900,
    SERIES_ORDER, FONT_STACK,
)

st.set_page_config(page_title="Sprint Overview", page_icon="🎯", layout="wide")

team = st.session_state.get("team", ALL_TEAMS)
assignee = st.session_state.get("assignee", ALL_ASSIGNEES)
team_label = TEAM_DISPLAY.get(team, team) if team != ALL_TEAMS else ""
title_suffix = f" — {team_label}" if team_label else ""
st.markdown(f"## 🎯 Sprint Overview{title_suffix}")

active_sprints = get_sprint_snapshots()
if not active_sprints:
    st.warning("No active sprints found. Run `/update-sprint-analytics` to fetch data.")
    st.stop()

# ── All-Sprints Summary ─────────────────────────────────────────────
section_header("All Sprints Summary")

combined = get_combined_sprint_metrics(team)
per_sprint = combined.get("per_sprint", [])

sprint_colors = [RED, BLUE, ORANGE, LIGHTBLUE]

cols = st.columns(len(per_sprint) + 1)

for i, sp in enumerate(per_sprint):
    color = sprint_colors[i % len(sprint_colors)]
    ratio = sp.get("commitment_ratio", 0)
    with cols[i]:
        st.markdown(
            f'<div style="background:{GRAY_100};border-radius:12px;padding:16px 12px;'
            f'text-align:center;border-top:4px solid {color};">'
            f'<div style="font-size:12px;font-weight:700;color:{GRAY_700};'
            f'margin-bottom:8px;">{sp["sprint_name"]}</div>'
            f'<div style="font-size:11px;color:{GRAY_500};">Committed</div>'
            f'<div style="font-size:22px;font-weight:700;color:{GRAY_900};">'
            f'{sp["committed_sp"]:.1f} SP</div>'
            f'<div style="font-size:11px;color:{GRAY_500};margin-top:6px;">Completed</div>'
            f'<div style="font-size:22px;font-weight:700;color:{color};">'
            f'{sp["completed_sp"]:.1f} SP</div>'
            f'<div style="font-size:11px;color:{GRAY_500};margin-top:6px;">Completion</div>'
            f'<div style="font-size:18px;font-weight:700;color:'
            f'{BLUE if ratio >= 0.8 else RED};">{ratio:.0%}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

total_ratio = combined.get("commitment_ratio", 0)
with cols[-1]:
    st.markdown(
        f'<div style="background:{GRAY_100};border-radius:12px;padding:16px 12px;'
        f'text-align:center;border-top:4px solid {ORANGE};">'
        f'<div style="font-size:12px;font-weight:700;color:{GRAY_700};'
        f'margin-bottom:8px;">TOTAL</div>'
        f'<div style="font-size:11px;color:{GRAY_500};">Committed</div>'
        f'<div style="font-size:22px;font-weight:700;color:{GRAY_900};">'
        f'{combined["committed_sp"]:.1f} SP</div>'
        f'<div style="font-size:11px;color:{GRAY_500};margin-top:6px;">Completed</div>'
        f'<div style="font-size:22px;font-weight:700;color:{ORANGE};">'
        f'{combined["completed_sp"]:.1f} SP</div>'
        f'<div style="font-size:11px;color:{GRAY_500};margin-top:6px;">Completion</div>'
        f'<div style="font-size:18px;font-weight:700;color:'
        f'{BLUE if total_ratio >= 0.8 else RED};">{total_ratio:.0%}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Comparison bar chart ─────────────────────────────────────────────
st.divider()
section_header("Committed vs Completed by Sprint")

sprint_names = [sp["sprint_name"] for sp in per_sprint] + ["TOTAL"]
committed_vals = [sp["committed_sp"] for sp in per_sprint] + [combined["committed_sp"]]
completed_vals = [sp["completed_sp"] for sp in per_sprint] + [combined["completed_sp"]]

fig_comp = go.Figure()
fig_comp.add_trace(go.Bar(
    x=sprint_names, y=committed_vals, name="Committed SP",
    marker_color=BLUE,
    text=[f"{v:.1f}" for v in committed_vals], textposition="outside",
))
fig_comp.add_trace(go.Bar(
    x=sprint_names, y=completed_vals, name="Completed SP",
    marker_color=LIGHTBLUE,
    text=[f"{v:.1f}" for v in completed_vals], textposition="outside",
))
fig_comp.update_layout(
    barmode="group", yaxis_title="Story Points",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(apply_chart_defaults(fig_comp, height=380), width="stretch")

# ── Selected Sprint Detail ───────────────────────────────────────────
st.divider()
sprint_name = st.session_state.get("sprint_name")
if not sprint_name or sprint_name == "Board Snapshot":
    sprint_name = active_sprints[0]

section_header(f"Sprint Detail — {sprint_name}")

metrics = get_snapshot_metrics(sprint_name, team)
df = get_snapshot_issues(sprint_name, team, assignee)

if not metrics:
    st.info("No metrics for this sprint.")
    st.stop()

ratio = metrics.get("commitment_ratio", 0)
kpi_row([
    {"label": "Committed SP", "value": f"{metrics.get('committed_sp', 0):.1f}", "color": BLUE},
    {"label": "Completed SP", "value": f"{metrics.get('completed_sp', 0):.1f}", "color": LIGHTBLUE},
    {"label": "Velocity", "value": int(metrics.get("velocity", 0)), "color": ORANGE},
    {
        "label": "Commitment Ratio",
        "value": f"{ratio:.0%}",
        "delta": "Target ≥ 80%",
        "color": BLUE if ratio >= 0.8 else RED,
    },
    {"label": "Carry-Over SP", "value": f"{metrics.get('carry_over_sp', 0):.1f}", "color": RED},
])

if metrics.get("unestimated_subtasks", 0) > 0:
    st.warning(f"⚠️ {metrics['unestimated_subtasks']} sub-tasks have no story points.")

st.divider()

if not df.empty:
    sprint_df = df[~df["status"].isin(NOT_IN_SPRINT_STATUSES)]
    col_chart, col_table = st.columns([2, 3])

    with col_chart:
        section_header("Status Distribution")
        status_counts = sprint_df.groupby("status")["key"].count().reset_index()
        status_counts.columns = ["status", "count"]

        color_map = {
            "Selected": LIGHTBLUE,
            "Selected for Development": LIGHTBLUE,
            "Ready for Sprint": BLUE,
            "In Progress": ORANGE,
            "Rejected / On Hold": RED,
            "On Hold": RED,
            "Rejected": RED,
            "Submitted": BLUE,
            "Awaiting Feedback": BLUE,
            "Feedback": BLUE,
            "Done": LIGHTBLUE,
        }
        colors = [color_map.get(s, GRAY_500) for s in status_counts["status"]]

        fig = go.Figure(go.Pie(
            labels=status_counts["status"],
            values=status_counts["count"],
            marker=dict(colors=colors),
            hole=0.4,
            textinfo="label+percent+value",
            textfont_size=11,
        ))
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(apply_chart_defaults(fig, height=380), width="stretch")

    with col_table:
        section_header("Sprint Issues")
        display_cols = [c for c in ["key", "summary", "issue_type", "status",
                                     "assignee", "story_points", "team"] if c in df.columns]
        st.dataframe(
            sprint_df[display_cols].sort_values(["status", "assignee"]),
            width="stretch", hide_index=True,
        )
