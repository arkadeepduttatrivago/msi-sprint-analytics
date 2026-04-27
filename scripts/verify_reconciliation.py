"""Verify Sprint Overview metrics == sum of Team Breakdown metrics across snapshots."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "sprints.json"
d = json.loads(DATA.read_text(encoding="utf-8"))

# Mapping of overview field -> team field
COMPARISONS = [
    ("committed_sp",   "committed_sp"),
    ("completed_sp",   "completed_sp"),
    ("velocity",       "velocity"),
    ("commitment_ratio", "commitment_ratio"),
]
COUNT_COMPARISONS = [
    ("committed_count", "committed_count"),
    ("completed_count", "completed_count"),
]

print(f"{'Sprint':25} {'Field':22} {'Overview':>10} {'TeamSum':>10} {'Match':>8}")
print("-" * 80)

all_match = True
for snap in d.get("snapshots", []):
    name = snap["sprint_name"]
    state = snap["sprint_state"]
    metrics = snap["metrics"]
    teams = snap["team_metrics"]
    print(f"\n{name} ({state})")
    teams_present = list(teams.keys())
    print(f"  Teams in team_metrics: {teams_present}")

    issue_team_set = sorted({i.get("team", "Unknown") for i in snap.get("issues", [])})
    print(f"  Teams seen in issues:  {issue_team_set}")

    if "Unknown" in issue_team_set:
        unknowns = [i["key"] for i in snap["issues"] if i.get("team") == "Unknown"]
        print(f"  ! Unknown issues:      {unknowns}")

    for ov_key, tm_key in COMPARISONS + COUNT_COMPARISONS:
        ov = metrics.get(ov_key, 0)
        if ov_key in {"velocity", "commitment_ratio"}:
            continue
        ts = sum(t.get(tm_key, 0) for t in teams.values())
        match = "OK" if abs((ov or 0) - (ts or 0)) < 0.01 else "FAIL"
        if match == "FAIL":
            all_match = False
        print(f"  {ov_key:22} {ov:>10} {ts:>10}  {match:>8}")

print("\n" + ("=" * 80))
print("ALL RECONCILED" if all_match else "RECONCILIATION FAILURES PRESENT")
