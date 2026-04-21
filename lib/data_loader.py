"""Load sprint data from the local JSON data store (no Jira connection).

Supports board-wide AND team-filtered views. When *team* is ``None`` or
``"All Teams"``, functions return board-wide aggregates (backward-compatible).
When a specific team label is passed, metrics come from the per-team
``team_metrics`` dict built by ``build_data.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "sprints.json"

COMPLETED_STATUSES = {"Feedback", "Done", "Submitted", "Awaiting Feedback"}
NOT_IN_SPRINT_STATUSES = {"Backlog", "Completed", "Completed: Not Part of Sprint"}
ALL_TEAMS = "All Teams"
ALL_ASSIGNEES = "All Assignees"
TEAM_DISPLAY = {
    "MSI_BRAND_CIM": "Brand & CIM",
    "MSI_EXP": "Experimentation",
    "MSI_OPS": "Operations",
    "Unknown": "Unassigned",
}


@st.cache_data
def load_data() -> dict:
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_snapshot_names() -> list[str]:
    data = load_data()
    return [s["sprint_name"] for s in data.get("snapshots", [])]


def get_sprint_snapshots() -> list[str]:
    """Return only real sprint names (exclude Board Snapshot)."""
    return [n for n in get_snapshot_names() if n != "Board Snapshot"]


def get_team_names() -> list[str]:
    """Return team labels present in the latest data."""
    data = load_data()
    teams: set[str] = set()
    for s in data.get("snapshots", []):
        tm = s.get("team_metrics", {})
        teams.update(tm.keys())
    return sorted(teams)


def get_all_assignees() -> list[str]:
    """Return sorted unique assignees across all issues."""
    data = load_data()
    assignees: set[str] = set()
    for s in data.get("snapshots", []):
        for issue in s.get("issues", []):
            a = issue.get("assignee", "Unassigned")
            if a and a != "Unassigned":
                assignees.add(a)
    return sorted(assignees)


def get_snapshot(sprint_name: str) -> dict | None:
    data = load_data()
    for s in data.get("snapshots", []):
        if s["sprint_name"] == sprint_name:
            return s
    return None


def _team_filter_active(team: str | None) -> bool:
    return team is not None and team != ALL_TEAMS


def get_snapshot_issues(
    sprint_name: str,
    team: str | None = None,
    assignee: str | None = None,
) -> pd.DataFrame:
    snap = get_snapshot(sprint_name)
    if not snap or not snap.get("issues"):
        return pd.DataFrame()
    df = pd.DataFrame(snap["issues"])
    df["story_points"] = pd.to_numeric(df["story_points"], errors="coerce").fillna(0)
    if _team_filter_active(team):
        df = df[df["team"] == team]
    if assignee and assignee != ALL_ASSIGNEES:
        df = df[df["assignee"] == assignee]
    return df


def get_snapshot_metrics(sprint_name: str, team: str | None = None) -> dict:
    snap = get_snapshot(sprint_name)
    if not snap:
        return {}
    if _team_filter_active(team):
        tm = snap.get("team_metrics", {})
        if team in tm:
            return tm[team]
        return _compute_team_metrics_fallback(snap, team)
    return snap.get("metrics", {})


def _compute_team_metrics_fallback(snap: dict, team: str) -> dict:
    """Backward-compatible: compute team metrics on-the-fly when
    ``team_metrics`` is missing from older snapshots."""
    issues = [i for i in snap.get("issues", []) if i.get("team") == team]
    if not issues:
        return {}
    committed = [i for i in issues if i["status"] not in NOT_IN_SPRINT_STATUSES]
    completed = [i for i in issues if i["status"] in COMPLETED_STATUSES]
    c_sp = sum(i.get("story_points", 0) for i in committed)
    d_sp = sum(i.get("story_points", 0) for i in completed)
    person_map: dict[str, dict] = defaultdict(
        lambda: {"committed_sp": 0, "completed_sp": 0, "count": 0}
    )
    for i in committed:
        person_map[i["assignee"]]["committed_sp"] += i.get("story_points", 0)
        person_map[i["assignee"]]["count"] += 1
    for i in completed:
        person_map[i["assignee"]]["completed_sp"] += i.get("story_points", 0)
    per_person = [
        {"assignee": k, **v}
        for k, v in sorted(person_map.items(), key=lambda x: -x[1]["completed_sp"])
    ]
    return {
        "committed_sp": c_sp,
        "completed_sp": d_sp,
        "velocity": d_sp,
        "committed_count": len(committed),
        "completed_count": len(completed),
        "commitment_ratio": round(d_sp / c_sp, 3) if c_sp else 0,
        "carry_over_sp": c_sp - d_sp,
        "carry_over_count": len(committed) - len(completed),
        "unestimated_subtasks": sum(
            1 for i in issues if i.get("story_points", 0) == 0
            and i.get("issue_type") == "Sub-task"
        ),
        "per_person": per_person,
        "per_team": [{"team": team, "committed_sp": c_sp, "completed_sp": d_sp}],
    }


def get_combined_sprint_metrics(team: str | None = None) -> dict:
    """Aggregate metrics across ALL active sprints (exclude Board Snapshot).

    Returns a dict with the same shape as a single snapshot's metrics, plus
    a ``per_sprint`` list of {sprint_name, committed_sp, completed_sp, ratio}.
    """
    sprints = get_sprint_snapshots()
    per_sprint = []
    total_committed = 0.0
    total_completed = 0.0
    total_carry = 0.0
    total_committed_count = 0
    total_completed_count = 0
    for sp in sprints:
        m = get_snapshot_metrics(sp, team)
        if not m:
            continue
        c = m.get("committed_sp", 0)
        d = m.get("completed_sp", 0)
        total_committed += c
        total_completed += d
        total_carry += m.get("carry_over_sp", 0)
        total_committed_count += m.get("committed_count", 0)
        total_completed_count += m.get("completed_count", 0)
        per_sprint.append({
            "sprint_name": sp,
            "committed_sp": c,
            "completed_sp": d,
            "commitment_ratio": round(d / c, 3) if c else 0,
            "carry_over_sp": m.get("carry_over_sp", 0),
        })
    ratio = round(total_completed / total_committed, 3) if total_committed else 0
    return {
        "committed_sp": total_committed,
        "completed_sp": total_completed,
        "velocity": total_completed,
        "commitment_ratio": ratio,
        "carry_over_sp": total_carry,
        "committed_count": total_committed_count,
        "completed_count": total_completed_count,
        "per_sprint": per_sprint,
    }


def get_all_snapshots_metrics(team: str | None = None) -> pd.DataFrame:
    data = load_data()
    rows = []
    for s in data.get("snapshots", []):
        if _team_filter_active(team):
            tm = s.get("team_metrics", {})
            m = dict(tm.get(team, {}))
        else:
            m = dict(s.get("metrics", {}))
        m["sprint_name"] = s["sprint_name"]
        m["sprint_state"] = s.get("sprint_state")
        m["sprint_start"] = s.get("sprint_start")
        m["sprint_end"] = s.get("sprint_end")
        rows.append(m)
    df = pd.DataFrame(rows)
    if not df.empty and "velocity" in df.columns:
        df["rolling_avg"] = df["velocity"].rolling(window=3, min_periods=1).mean()
    return df


def get_epic_progress(team: str | None = None) -> pd.DataFrame:
    data = load_data()
    epics = data.get("epics", [])
    if not epics:
        return pd.DataFrame()
    df = pd.DataFrame(epics)
    if _team_filter_active(team):
        df = df[df["team"] == team]
    return df


def get_last_updated() -> str:
    data = load_data()
    return data.get("last_updated", "Never")


def reload_data():
    """Clear the cache so the next call re-reads from disk."""
    load_data.clear()
