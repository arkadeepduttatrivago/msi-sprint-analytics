"""Quick verification that the data store loads correctly."""
import sys
sys.path.insert(0, ".")
from lib.data_loader import load_data, get_snapshot_names, get_epic_progress

d = load_data()
print(f"Snapshots: {get_snapshot_names()}")
ep = get_epic_progress()
print(f"Epics: {len(ep)} rows")
print(f"Last updated: {d.get('last_updated')}")

snap = d.get("snapshots", [{}])[0]
m = snap.get("metrics", {})
print(f"Committed SP: {m.get('committed_sp', 0)}")
print(f"Completed SP: {m.get('completed_sp', 0)}")
print(f"Unestimated: {m.get('unestimated_subtasks', 0)}")
print(f"Issues in snapshot: {len(snap.get('issues', []))}")
