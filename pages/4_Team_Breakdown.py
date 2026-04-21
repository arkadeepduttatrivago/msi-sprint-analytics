"""Page 4: Team Breakdown — per-team KPIs with assignee detail."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from lib.data_loader import (
    get_snapshot_metrics, get_snapshot_issues,
    get_team_names, TEAM_DISPLAY, ALL_TEAMS,
)
from lib.brand import (
    kpi_row, section_header, apply_chart_defaults,
    GRAY_300, GRAY_500, GRAY_900, TEAM_COLORS, BLUE, ORANGE, LIGHTBLUE,
)

st.set_page_config(page_title="Team Breakdown", page_icon="👥", layout="wide")
st.markdown("## 👥 Team Breakdown")

sprint_name = st.session_state.get("sprint_name")
if not sprint_name:
    st.warning("Select a sprint from the sidebar.")
    st.stop()

teams = get_team_names()

section_header(f"Team Comparison — {sprint_name}")

cols = st.columns(len(teams))
for col, t in zip(cols, teams):
    tm = get_snapshot_metrics(sprint_name, t)
    display_name = TEAM_DISPLAY.get(t, t)
    color = TEAM_COLORS.get(t, GRAY_300)
    ratio = tm.get("commitment_ratio", 0) if tm else 0
    with col:
        st.markdown(
            f'<div style="text-align:center;padding:8px 0;border-top:4px solid {color};">'
            f'<div style="font-weight:700;font-size:15px;color:{GRAY_900};">{display_name}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if tm:
            st.metric("Committed SP", f"{tm.get('committed_sp', 0):.1f}")
            st.metric("Completed SP", f"{tm.get('completed_sp', 0):.1f}")
            st.metric("Completion Rate", f"{ratio:.0%}")
            if tm.get("unestimated_subtasks", 0) > 0:
                st.caption(f"⚠️ {tm['unestimated_subtasks']} unestimated")
        else:
            st.caption("No data")

st.divider()
section_header(f"Assignee Breakdown by Team — {sprint_name}")

df = get_snapshot_issues(sprint_name)
if not df.empty:
    person_team = (
        df.groupby(["team", "assignee"])["story_points"]
        .sum()
        .reset_index()
        .sort_values(["team", "story_points"], ascending=[True, False])
    )
    person_team["display_team"] = person_team["team"].map(TEAM_DISPLAY).fillna(
        person_team["team"]
    )

    fig = go.Figure()
    for t in teams:
        subset = person_team[person_team["team"] == t]
        if subset.empty:
            continue
        fig.add_trace(go.Bar(
            y=subset["assignee"],
            x=subset["story_points"],
            orientation="h",
            name=TEAM_DISPLAY.get(t, t),
            marker_color=TEAM_COLORS.get(t, GRAY_300),
            text=subset["story_points"].apply(lambda v: f"{v:.1f}"),
            textposition="outside",
        ))
    fig.update_layout(
        xaxis_title="Story Points",
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(
        apply_chart_defaults(fig, height=max(400, len(person_team) * 40)),
        width="stretch",
    )
else:
    st.caption("No issue data for this sprint.")

st.divider()
section_header(f"Committed vs Completed by Team — {sprint_name}")

board_metrics = get_snapshot_metrics(sprint_name)
pt = board_metrics.get("per_team", []) if board_metrics else []
if pt:
    team_df = pd.DataFrame(pt)
    team_df["display"] = team_df["team"].map(TEAM_DISPLAY).fillna(team_df["team"])

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=team_df["display"], y=team_df["committed_sp"],
        name="Committed SP", marker_color=BLUE,
        text=team_df["committed_sp"].apply(lambda v: f"{v:.0f}"),
        textposition="outside",
    ))
    fig2.add_trace(go.Bar(
        x=team_df["display"], y=team_df["completed_sp"],
        name="Completed SP", marker_color=LIGHTBLUE,
        text=team_df["completed_sp"].apply(lambda v: f"{v:.0f}"),
        textposition="outside",
    ))
    fig2.update_layout(
        yaxis_title="Story Points", barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(apply_chart_defaults(fig2), width="stretch")
else:
    st.caption("No team data for this sprint.")
