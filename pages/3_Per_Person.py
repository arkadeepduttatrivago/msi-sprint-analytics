"""Page 3: Per-Person — story points per assignee across sprints."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from lib.data_loader import (
    get_snapshot_issues, get_sprint_snapshots,
    TEAM_DISPLAY, ALL_TEAMS, ALL_ASSIGNEES, NOT_IN_SPRINT_STATUSES,
)
from lib.brand import (
    section_header, apply_chart_defaults,
    BLUE, ORANGE, RED, LIGHTBLUE, PINK, YELLOW,
    GRAY_100, GRAY_500, GRAY_700, GRAY_900, SERIES_ORDER,
)

st.set_page_config(page_title="Per-Person", page_icon="👤", layout="wide")

team = st.session_state.get("team", ALL_TEAMS)
assignee = st.session_state.get("assignee", ALL_ASSIGNEES)
team_label = TEAM_DISPLAY.get(team, team) if team != ALL_TEAMS else ""
title_suffix = f" — {team_label}" if team_label else ""
st.markdown(f"## 👤 Per-Person{title_suffix}")

active_sprints = get_sprint_snapshots()
if not active_sprints:
    st.warning("No active sprints. Run `/update-sprint-analytics`.")
    st.stop()

# ── Page-level sprint selector ───────────────────────────────────────
selected_sprints = st.multiselect(
    "Select Sprints",
    active_sprints,
    default=active_sprints,
    help="Choose one or more sprints to view per-person breakdown.",
)
if not selected_sprints:
    st.info("Select at least one sprint.")
    st.stop()

# ── Gather data across selected sprints ──────────────────────────────
rows: list[dict] = []
for sp in selected_sprints:
    df = get_snapshot_issues(sp, team, assignee)
    if df.empty:
        continue
    sprint_df = df[~df["status"].isin(NOT_IN_SPRINT_STATUSES)]
    for _, r in sprint_df.iterrows():
        rows.append({
            "sprint": sp,
            "assignee": r.get("assignee", "Unassigned"),
            "story_points": float(r.get("story_points", 0)),
            "status": r.get("status", ""),
        })

if not rows:
    st.info("No in-sprint data for the selected sprints.")
    st.stop()

all_df = pd.DataFrame(rows)

# ── Person × Sprint grouped bar chart ────────────────────────────────
section_header("Story Points by Person & Sprint")

pivot = (
    all_df.groupby(["assignee", "sprint"])["story_points"]
    .sum()
    .reset_index()
)
person_totals = pivot.groupby("assignee")["story_points"].sum().sort_values(ascending=True)
person_order = person_totals.index.tolist()

fig = go.Figure()
for i, sp in enumerate(selected_sprints):
    sp_data = pivot[pivot["sprint"] == sp].set_index("assignee").reindex(person_order).fillna(0)
    fig.add_trace(go.Bar(
        y=sp_data.index,
        x=sp_data["story_points"],
        orientation="h",
        name=sp,
        marker_color=SERIES_ORDER[i % len(SERIES_ORDER)],
        text=sp_data["story_points"].apply(lambda v: f"{v:.1f}" if v > 0 else ""),
        textposition="outside",
    ))

fig.update_layout(
    barmode="group",
    xaxis_title="Story Points",
    yaxis=dict(categoryorder="array", categoryarray=person_order),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(
    apply_chart_defaults(fig, height=max(350, len(person_order) * 55)),
    width="stretch",
)

# ── Summary KPI per person ───────────────────────────────────────────
st.divider()
section_header("Person Summary Table")

from lib.data_loader import COMPLETED_STATUSES

summary = (
    all_df.groupby("assignee")
    .agg(
        total_sp=("story_points", "sum"),
        tickets=("story_points", "count"),
    )
    .reset_index()
)

completed_sp = (
    all_df[all_df["status"].isin(COMPLETED_STATUSES)]
    .groupby("assignee")["story_points"]
    .sum()
    .reset_index()
    .rename(columns={"story_points": "completed_sp"})
)
summary = summary.merge(completed_sp, on="assignee", how="left").fillna(0)
summary["completion"] = summary.apply(
    lambda r: f"{r['completed_sp'] / r['total_sp']:.0%}" if r["total_sp"] > 0 else "0%",
    axis=1,
)
summary = summary.sort_values("total_sp", ascending=False)
summary.columns = ["Assignee", "Total SP", "Tickets", "Completed SP", "Completion %"]

st.dataframe(summary, width="stretch", hide_index=True)
