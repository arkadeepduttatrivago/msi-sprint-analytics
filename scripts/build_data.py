"""Process raw MCP Jira output into the sprint analytics data store.

Reads the latest file from data/raw/, extracts issues, groups by sprint,
computes metrics, and merges into data/sprints.json (preserving history).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
RAW_DIR = BASE / "data" / "raw"
DATA_FILE = BASE / "data" / "sprints.json"

# Status taxonomy — TWO RULE SETS that intentionally differ.
#
# Rule A: SPRINT context (Sprint Overview, Per Person, Velocity, Completion)
#   "Committed in this sprint" = whole board: Selected for Development,
#                                Selected, Ready for Sprint, On Hold,
#                                Rejected, Rejected / On Hold,
#                                In Progress, plus SPRINT_DONE
#   "Done in this sprint"      = Feedback, Submitted, Awaiting Feedback,
#                                Done, Completed
#   Excluded                   = Backlog, Stacked, Stacked Old,
#                                Completed : Not Part of Sprint,
#                                Completed Not Part of Sprint
#
# Rule B: INITIATIVE context (epic/milestone progress, Initiatives tab)
#   "Done"     = Feedback, Submitted, Awaiting Feedback, Done, Completed,
#                Completed : Not Part of Sprint,
#                Completed Not Part of Sprint, Stacked, Stacked Old
#   "Not done" = everything else
#
# These differ because:
#   - A subtask completed outside its sprint still moves initiative
#     progress forward, even though it does not contribute to THAT
#     sprint's velocity.
#   - A subtask in Feedback / Submitted / Awaiting Feedback is "done
#     enough" for initiative progress (work is delivered, awaiting
#     review) but is the last lap for sprint velocity, not the finish
#     line.

SPRINT_DONE_STATUSES = {
    "Feedback", "Submitted", "Awaiting Feedback", "Done", "Completed",
}
SPRINT_IN_PROGRESS_STATUSES = {"In Progress"}
SPRINT_COMMITTED_STATUSES = (
    {
        "Selected for Development", "Selected",
        "Ready for Sprint",
        "On Hold", "Rejected", "Rejected / On Hold",
    }
    | SPRINT_IN_PROGRESS_STATUSES
    | SPRINT_DONE_STATUSES
)
# Backwards-compat aliases — older code in this file still references these.
COMPLETED_STATUSES = SPRINT_DONE_STATUSES
NOT_IN_SPRINT_STATUSES = {
    "Backlog",
    "Stacked", "Stacked Old",
    "Completed: Not Part of Sprint",
    "Completed : Not Part of Sprint",
    "Completed Not Part of Sprint",
}

INITIATIVE_DONE_STATUSES = {
    "Feedback", "Submitted", "Awaiting Feedback",
    "Done", "Completed",
    "Completed: Not Part of Sprint",
    "Completed : Not Part of Sprint",
    "Completed Not Part of Sprint",
    "Stacked", "Stacked Old",
}
TEAM_LABELS = {"MSI_OPS", "MSI_EXP", "MSI_BRAND_CIM"}
BOARD_ID = 7527
BAU_EPIC = "MSI-1839"
ADHOC_EPIC = "MSI-1840"

# Sprint-name -> team mapping. The sprint container is the source of truth
# for "which team is doing this work right now". A ticket sitting in
# MSI_OPS_SPRINT_2 is OPS work for that sprint, regardless of its labels.
# Order matters: longer prefixes must come first so MSI_BRAND_CIM beats
# any shorter MSI_ prefix that might be added in future.
SPRINT_TEAM_PREFIXES: list[tuple[str, str]] = [
    ("MSI_BRAND_CIM_SPRINT_", "MSI_BRAND_CIM"),
    ("BRAND_CIM_SPRINT_",     "MSI_BRAND_CIM"),
    ("MSI_OPS_SPRINT_",       "MSI_OPS"),
    ("MSI_EXP_SPRINT_",       "MSI_EXP"),
]


def team_from_sprint_name(sprint_name: str | None) -> str | None:
    """Return the team derived from a sprint container name, or None."""
    if not sprint_name:
        return None
    for prefix, team in SPRINT_TEAM_PREFIXES:
        if sprint_name.startswith(prefix):
            return team
    return None

STATUS_NORMALIZE: dict[str, str] = {
    "READY FOR SPRINT": "Ready for Sprint",
    "SELECTED FOR DEVELOPMENT": "Selected for Development",
    "SELECTED": "Selected",
    "IN PROGRESS": "In Progress",
    "REJECTED / ON HOLD": "Rejected / On Hold",
    "ON HOLD": "On Hold",
    "REJECTED": "Rejected",
    "SUBMITTED": "Submitted",
    "AWAITING FEEDBACK": "Awaiting Feedback",
    "FEEDBACK": "Feedback",
    "DONE": "Done",
    "COMPLETED": "Completed",
    "COMPLETED: NOT PART OF SPRINT": "Completed: Not Part of Sprint",
    "COMPLETED : NOT PART OF SPRINT": "Completed : Not Part of Sprint",
    "COMPLETED NOT PART OF SPRINT": "Completed Not Part of Sprint",
    "STACKED": "Stacked",
    "STACKED OLD": "Stacked Old",
}


def normalize_status(raw_name: str) -> str:
    return STATUS_NORMALIZE.get(raw_name.upper().strip(), raw_name)


def find_latest_raw() -> Path:
    files = sorted(RAW_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    if not files:
        print("ERROR: No raw data files in data/raw/. Run /update-sprint-analytics first.")
        sys.exit(1)
    return files[0]


def extract_issue(raw: dict) -> dict:
    f = raw.get("fields", {})
    status = f.get("status", {})
    assignee = f.get("assignee")
    parent = f.get("parent")
    labels = f.get("labels", [])

    sprint_data = f.get("customfield_10020") or f.get("sprint")
    sprint_name = None
    sprint_state = None
    sprint_start = None
    sprint_end = None
    if isinstance(sprint_data, list) and sprint_data:
        board_sprints = [s for s in sprint_data
                         if isinstance(s, dict) and s.get("boardId") == BOARD_ID]
        if board_sprints:
            latest = max(board_sprints, key=lambda s: s.get("id", 0))
            sprint_name = latest.get("name")
            sprint_state = latest.get("state")
            sprint_start = latest.get("startDate", "")[:10] if latest.get("startDate") else None
            sprint_end = latest.get("endDate", "")[:10] if latest.get("endDate") else None
    elif isinstance(sprint_data, dict):
        if sprint_data.get("boardId") == BOARD_ID or "boardId" not in sprint_data:
            sprint_name = sprint_data.get("name")
            sprint_state = sprint_data.get("state")
            sprint_start = sprint_data.get("startDate", "")[:10] if sprint_data.get("startDate") else None
            sprint_end = sprint_data.get("endDate", "")[:10] if sprint_data.get("endDate") else None

    # Team derivation. Source-of-truth order:
    #   1. Sprint container name (MSI_OPS_SPRINT_1 -> MSI_OPS).
    #   2. Team label on the ticket (MSI_OPS / MSI_EXP / MSI_BRAND_CIM).
    #   3. "Unknown" — only if no sprint and no label.
    # The sprint wins over the label so cross-team work (e.g. a Brand-
    # labelled sub-task pulled into OPS Sprint 1) gets attributed to the
    # team actually executing it that sprint. This makes the dashboard's
    # Sprint Overview totals reconcile with the Team Breakdown totals.
    team = team_from_sprint_name(sprint_name)
    if team is None:
        for lbl in labels:
            if lbl in TEAM_LABELS:
                team = lbl
                break
    if team is None:
        team = "Unknown"

    return {
        "key": raw.get("key", ""),
        "summary": f.get("summary", ""),
        "status": normalize_status(status.get("name", "Unknown")),
        "status_category": status.get("statusCategory", {}).get("name", "Unknown"),
        "issue_type": f.get("issuetype", {}).get("name", "Unknown"),
        "hierarchy_level": f.get("issuetype", {}).get("hierarchyLevel", 0),
        "assignee": assignee["displayName"] if assignee else "Unassigned",
        "parent_key": parent["key"] if parent else None,
        "parent_summary": parent.get("fields", {}).get("summary", "") if parent else None,
        "labels": labels,
        "team": team,
        "story_points": float(f.get("customfield_10033") or f.get("customfield_10016") or 0),
        "due_date": f.get("duedate"),
        "resolution_date": f.get("resolutiondate"),
        "sprint_name": sprint_name,
        "sprint_state": sprint_state,
        "sprint_start": sprint_start,
        "sprint_end": sprint_end,
    }


def is_committed(status: str) -> bool:
    """Sprint-context: was this ticket committed to its sprint?
    True for Selected for Development onwards. Excludes Backlog,
    Ready for Sprint, On Hold/Rejected, Stacked, and the
    out-of-sprint Completed* variants."""
    return status in SPRINT_COMMITTED_STATUSES


def is_completed(status: str) -> bool:
    """Sprint-context: did this ticket complete IN its sprint?
    True for Feedback, Submitted, Awaiting Feedback, Done, Completed.
    Out-of-sprint Completed variants are excluded — they did not
    contribute to that sprint's velocity."""
    return status in SPRINT_DONE_STATUSES


def is_initiative_done(status: str) -> bool:
    """Initiative-context: did this work ever finish, regardless of sprint?
    True for Done, Completed, both Completed-Not-Part-of-Sprint variants,
    and Stacked / Stacked Old. Used for milestone and epic progress in
    the Initiatives tab. Broader than is_completed(), which is
    sprint-scoped."""
    return status in INITIATIVE_DONE_STATUSES


def assign_categories(issues: list[dict]) -> None:
    """Tag each issue with 'bau', 'adhoc', or 'okr' based on epic ancestry."""
    by_key = {i["key"]: i for i in issues}

    def find_epic_key(issue: dict) -> str | None:
        visited: set[str] = set()
        cur = issue
        while cur:
            if cur["key"] in visited:
                break
            visited.add(cur["key"])
            if cur["issue_type"] == "Epic":
                return cur["key"]
            pk = cur.get("parent_key")
            if pk and pk in by_key:
                cur = by_key[pk]
            else:
                return pk
        return None

    for issue in issues:
        epic_key = find_epic_key(issue)
        if epic_key == BAU_EPIC:
            issue["category"] = "bau"
        elif epic_key == ADHOC_EPIC:
            issue["category"] = "adhoc"
        else:
            issue["category"] = "okr"


def compute_sprint_metrics(issues: list[dict]) -> dict:
    committed = [i for i in issues if is_committed(i["status"])]
    completed = [i for i in issues if is_completed(i["status"])]

    committed_sp = sum(i["story_points"] for i in committed)
    completed_sp = sum(i["story_points"] for i in completed)

    # Per-person
    person_map: dict[str, dict] = defaultdict(lambda: {"committed_sp": 0, "completed_sp": 0, "count": 0})
    for i in committed:
        person_map[i["assignee"]]["committed_sp"] += i["story_points"]
        person_map[i["assignee"]]["count"] += 1
    for i in completed:
        person_map[i["assignee"]]["completed_sp"] += i["story_points"]
    per_person = [{"assignee": k, **v} for k, v in sorted(person_map.items(), key=lambda x: -x[1]["completed_sp"])]

    # Per-team
    team_map: dict[str, dict] = defaultdict(lambda: {"committed_sp": 0, "completed_sp": 0})
    for i in committed:
        team_map[i["team"]]["committed_sp"] += i["story_points"]
    for i in completed:
        team_map[i["team"]]["completed_sp"] += i["story_points"]
    per_team = [{"team": k, **v} for k, v in sorted(team_map.items())]

    unestimated = sum(1 for i in issues if i["story_points"] == 0 and i["issue_type"] == "Sub-task")

    return {
        "committed_sp": committed_sp,
        "completed_sp": completed_sp,
        "velocity": completed_sp,
        "committed_count": len(committed),
        "completed_count": len(completed),
        "commitment_ratio": round(completed_sp / committed_sp, 3) if committed_sp else 0,
        "carry_over_sp": committed_sp - completed_sp,
        "carry_over_count": len(committed) - len(completed),
        "unestimated_subtasks": unestimated,
        "per_person": per_person,
        "per_team": per_team,
    }


def compute_team_metrics(issues: list[dict]) -> dict[str, dict]:
    """Full metric set per team label, keyed by team name."""
    by_team: dict[str, list[dict]] = defaultdict(list)
    for i in issues:
        by_team[i["team"]].append(i)
    return {team: compute_sprint_metrics(team_issues)
            for team, team_issues in sorted(by_team.items())}


WEIGHTS_FILE = BASE / "data" / "milestone_weights.json"


def load_milestone_weights() -> dict[str, dict[str, float | None]]:
    if WEIGHTS_FILE.exists():
        with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def build_epic_progress(issues: list[dict]) -> list[dict]:
    """Weighted initiative completion based on subtask progress per milestone.

    Each milestone's completion = completed_subtasks / total_subtasks.
    KR completion = sum(weight_i * milestone_i_completion).
    Weights from milestone_weights.json; equal weights if absent.
    """
    weights_config = load_milestone_weights()
    epics = {i["key"]: i for i in issues if i["issue_type"] == "Epic"}
    tasks = {i["key"]: i for i in issues if i["issue_type"] == "Task"}
    subtasks = [i for i in issues if i["issue_type"] == "Sub-task"]

    subtask_by_parent: dict[str, list[dict]] = defaultdict(list)
    for st in subtasks:
        if st.get("parent_key"):
            subtask_by_parent[st["parent_key"]].append(st)

    result = []
    for key, epic in sorted(epics.items()):
        milestones = [t for t in tasks.values() if t["parent_key"] == key]
        epic_weights = weights_config.get(key, {})

        milestone_data = []
        for m in milestones:
            subs = subtask_by_parent.get(m["key"], [])
            total_subs = len(subs)
            done_subs = sum(1 for s in subs if is_initiative_done(s["status"]))
            if total_subs:
                m_progress = round(done_subs / total_subs, 3)
            elif is_initiative_done(m["status"]):
                m_progress = 1.0
            else:
                m_progress = 0.0

            raw_w = epic_weights.get(m["key"])
            milestone_data.append({
                "key": m["key"],
                "summary": m["summary"],
                "status": m["status"],
                "story_points": m["story_points"],
                "due_date": m["due_date"],
                "total_subtasks": total_subs,
                "done_subtasks": done_subs,
                "milestone_progress": m_progress,
                "weight": raw_w,
            })

        n = len(milestone_data)
        has_weights = any(md["weight"] is not None for md in milestone_data)
        if has_weights:
            for md in milestone_data:
                if md["weight"] is None:
                    md["weight"] = 0.0
        else:
            for md in milestone_data:
                md["weight"] = round(1.0 / n, 4) if n else 0.0

        kr_progress = sum(
            md["weight"] * md["milestone_progress"] for md in milestone_data
        )

        result.append({
            "epic_key": key,
            "summary": epic["summary"],
            "team": epic["team"],
            "total_milestones": n,
            "done_milestones": sum(
                1 for md in milestone_data if md["milestone_progress"] >= 1.0
            ),
            "progress": round(kr_progress, 4),
            "milestones": milestone_data,
        })
    return result


def merge_snapshots(stored_snapshots: list[dict],
                    fetched_snapshots: list[dict]) -> list[dict]:
    """Merge stored and fetched snapshots per the Snapshot Discipline rule.

    See `msi-jira-analytics` `SKILL.md` for the full truth table. Summary:
    closed snapshots are immutable; active→closed transitions flip state
    only (never overwrite metrics with a post-close fetch); orphaned
    stored snapshots are retained so history never disappears.

    Rule table (stored × fetch):
      not stored,      in fetch           -> append new
      stored active,   not in fetch       -> keep stored
      stored closed,   not in fetch       -> keep stored
      stored active,   fetch active       -> refresh from fetch
      stored active,   fetch closed       -> keep stored; flip state to closed
      stored closed,   fetch any          -> keep stored (immutable)
    """
    old_by_name = {s["sprint_name"]: s for s in stored_snapshots}
    new_by_name = {s["sprint_name"]: s for s in fetched_snapshots}

    merged: list[dict] = []
    for name in set(old_by_name) | set(new_by_name):
        stored = old_by_name.get(name)
        fetched = new_by_name.get(name)

        if stored is None:
            merged.append(fetched)
            continue
        if fetched is None:
            merged.append(stored)
            continue

        stored_state = stored.get("sprint_state")
        fetched_state = fetched.get("sprint_state")

        if stored_state == "closed":
            merged.append(stored)
        elif fetched_state == "closed":
            frozen = dict(stored)
            frozen["sprint_state"] = "closed"
            merged.append(frozen)
        else:
            merged.append(fetched)

    merged.sort(key=lambda s: s.get("sprint_start") or "9999")
    return merged


def main():
    raw_file = find_latest_raw()
    print(f"Reading raw data: {raw_file.name}")

    with open(raw_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, dict) and "issues" in raw_data:
        raw_issues = raw_data["issues"]
    elif isinstance(raw_data, list):
        raw_issues = raw_data
    else:
        print("ERROR: Unexpected raw data format.")
        sys.exit(1)

    issues = [extract_issue(r) for r in raw_issues]
    assign_categories(issues)
    print(f"Extracted {len(issues)} issues")

    type_counts = defaultdict(int)
    for i in issues:
        type_counts[i["issue_type"]] += 1
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")

    # Group by sprint
    sprint_groups: dict[str, list[dict]] = defaultdict(list)
    no_sprint = []
    for i in issues:
        if i["sprint_name"]:
            sprint_groups[i["sprint_name"]].append(i)
        else:
            no_sprint.append(i)

    # Build snapshots
    now = datetime.now(timezone.utc).isoformat()
    new_snapshots = []

    if sprint_groups:
        for sprint_name, sprint_issues in sorted(sprint_groups.items()):
            sample = sprint_issues[0]
            metrics = compute_sprint_metrics(sprint_issues)
            team_metrics = compute_team_metrics(sprint_issues)
            new_snapshots.append({
                "snapshot_date": now,
                "sprint_name": sprint_name,
                "sprint_state": sample["sprint_state"],
                "sprint_start": sample["sprint_start"],
                "sprint_end": sample["sprint_end"],
                "metrics": metrics,
                "team_metrics": team_metrics,
                "issues": sprint_issues,
            })
    else:
        metrics = compute_sprint_metrics(issues)
        team_metrics = compute_team_metrics(issues)
        new_snapshots.append({
            "snapshot_date": now,
            "sprint_name": "Board Snapshot",
            "sprint_state": "snapshot",
            "sprint_start": None,
            "sprint_end": None,
            "metrics": metrics,
            "team_metrics": team_metrics,
            "issues": issues,
        })

    existing = {"board_id": 7527, "snapshots": [], "epics": [], "all_issues_latest": []}
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)

    merged_snapshots = merge_snapshots(existing.get("snapshots", []), new_snapshots)

    # Build epic progress from ALL issues
    epic_progress = build_epic_progress(issues)

    output = {
        "last_updated": now,
        "board_id": 7527,
        "board_name": "MSI_OKR_SUMMER_2026",
        "snapshots": merged_snapshots,
        "epics": epic_progress,
        "all_issues_latest": issues,
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    size_kb = DATA_FILE.stat().st_size / 1024
    print(f"\nSPRINT ANALYTICS UPDATED")
    print(f"  Timestamp: {now}")
    print(f"  Total issues: {len(issues)}")
    for t, c in sorted(type_counts.items()):
        print(f"    {t}: {c}")
    print(f"  Sprint snapshots: {[s['sprint_name'] for s in merged_snapshots]}")
    print(f"  Epic progress entries: {len(epic_progress)}")
    team_counts = defaultdict(int)
    for i in issues:
        team_counts[i["team"]] += 1
    print(f"  Teams: {dict(sorted(team_counts.items()))}")
    print(f"  Data file: {DATA_FILE} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
