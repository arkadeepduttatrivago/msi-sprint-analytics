"""MSI OKR Sprint Analytics — Main entry point.

Reads from local data/sprints.json. No Jira credentials needed.
Run /update-sprint-analytics in Cursor to refresh data.
"""

import streamlit as st
from lib.data_loader import (
    get_snapshot_names, get_sprint_snapshots, get_last_updated, reload_data,
    get_team_names, get_all_assignees, ALL_TEAMS, ALL_ASSIGNEES, TEAM_DISPLAY,
)
from lib.brand import trv_logo_html, BLUE, LIGHTBLUE, GRAY_500, GRAY_900

st.set_page_config(
    page_title="MSI Sprint Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"{trv_logo_html()}"
        f'<div style="font-size:13px;color:{GRAY_500};margin-top:2px;">'
        "MSI Sprint Analytics</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    if st.button("🔄 Reload Data from Disk", width="stretch", type="primary"):
        reload_data()
        st.toast("Data reloaded from sprints.json", icon="🔄")
        st.rerun()

    last = get_last_updated()
    st.caption(f"Last updated: {last[:19] if len(last) > 19 else last}")
    st.caption(
        "Run `/update-sprint-analytics` in Cursor to fetch fresh Jira data."
    )
    st.divider()

    snapshots = get_snapshot_names()
    sprints = get_sprint_snapshots()
    if not snapshots:
        st.warning(
            "No data yet. Run `/update-sprint-analytics` in Cursor to fetch data."
        )
        st.stop()

    default_idx = snapshots.index(sprints[0]) if sprints else 0
    selected = st.selectbox("Select Sprint", snapshots, index=default_idx)
    st.session_state["sprint_name"] = selected

    st.divider()
    teams = get_team_names()
    team_options = [ALL_TEAMS] + teams
    team_labels = {ALL_TEAMS: "All Teams"}
    team_labels.update(TEAM_DISPLAY)
    selected_team = st.radio(
        "Filter by Team",
        team_options,
        format_func=lambda t: team_labels.get(t, t),
        index=0,
    )
    st.session_state["team"] = selected_team

    st.divider()
    assignees = get_all_assignees()
    assignee_options = [ALL_ASSIGNEES] + assignees
    selected_assignee = st.selectbox("Filter by Assignee", assignee_options, index=0)
    st.session_state["assignee"] = selected_assignee

    st.divider()
    st.markdown(
        f'<div style="font-size:10px;background:{LIGHTBLUE};color:#000;'
        f'padding:4px 12px;border-radius:4px;display:inline-block;">'
        "Created by trv-OS</div>",
        unsafe_allow_html=True,
    )

# ── Home page ─────────────────────────────────────────────────────────
st.markdown(
    f'<h1 style="color:{GRAY_900};font-size:28px;">📊 MSI OKR Sprint Analytics</h1>'
    f'<p style="color:{GRAY_500};font-size:14px;">'
    "Velocity · Burndown · Per-Person · Team · Initiative Progress</p>",
    unsafe_allow_html=True,
)

st.info(
    "👈 Use the **sidebar** to select a sprint and navigate between pages. "
    "Data is refreshed by running `/update-sprint-analytics` in Cursor.",
    icon="ℹ️",
)

col1, col2, col3 = st.columns(3)
col1.page_link("pages/1_Sprint_Overview.py", label="Sprint Overview", icon="🎯")
col2.page_link("pages/2_Velocity_Trends.py", label="Velocity Trends", icon="📈")
col3.page_link("pages/3_Per_Person.py", label="Per-Person", icon="👤")
col4, col5, col6 = st.columns(3)
col4.page_link("pages/4_Team_Breakdown.py", label="Team Breakdown", icon="👥")
col5.page_link("pages/5_Initiative_Progress.py", label="Initiatives", icon="🏔️")
col6.page_link("pages/6_Sprint_Completion.py", label="Sprint Completion", icon="📋")
