"""One-time migration: re-derive `issue.team` for all snapshots using the
sprint-name rule, then recompute `team_metrics`.

Why this exists: build_data.py was previously deriving team from labels
only. That worked for label-clean tickets but dropped any ticket that
sat in a sprint without a matching team label, producing reconciliation
errors between the Sprint Overview and Team Breakdown views in
index.html.

The new rule (in build_data.team_from_sprint_name) sources team from
the sprint container name first, falling back to label, then "Unknown".
This script applies that rule retroactively to already-stored
snapshots (which the Snapshot Discipline otherwise freezes).

Scope: changes only `issue.team` and `team_metrics`. Board-wide
`metrics` (committed_sp, completed_sp, etc.) are unchanged.

Usage: idempotent. Safe to re-run.
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "sprints.json"

sys.path.insert(0, str(BASE / "scripts"))
from build_data import team_from_sprint_name, compute_team_metrics

ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
backup = DATA.with_suffix(f".backup.{ts}.json")
shutil.copy2(DATA, backup)
print(f"Backup: {backup.name}")

d = json.loads(DATA.read_text(encoding="utf-8"))

changes = 0
TEAM_LABELS = {"MSI_OPS", "MSI_EXP", "MSI_BRAND_CIM"}

def derive_team(issue: dict) -> str:
    """Mirror build_data.extract_issue's team logic."""
    t = team_from_sprint_name(issue.get("sprint_name"))
    if t:
        return t
    for lbl in issue.get("labels", []) or []:
        if lbl in TEAM_LABELS:
            return lbl
    return "Unknown"

for snap in d.get("snapshots", []):
    name = snap.get("sprint_name")
    snap_changes = 0
    for iss in snap.get("issues", []):
        new_team = derive_team(iss)
        if iss.get("team") != new_team:
            iss["team"] = new_team
            snap_changes += 1
    snap["team_metrics"] = compute_team_metrics(snap["issues"])
    if snap_changes:
        print(f"  {name:25} corrected {snap_changes} team assignments")
    changes += snap_changes

for iss in d.get("all_issues_latest", []):
    new_team = derive_team(iss)
    if iss.get("team") != new_team:
        iss["team"] = new_team

d["last_updated"] = datetime.now(timezone.utc).isoformat()

DATA.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nTotal team corrections: {changes}")
print(f"Wrote: {DATA.relative_to(BASE)}")
