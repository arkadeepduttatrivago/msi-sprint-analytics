"""Merge paginated MCP response pages into a single raw file."""
import json
from pathlib import Path
from datetime import date

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

pages = sorted(RAW_DIR.glob("page*.json"))
all_issues = []
for p in pages:
    with open(p, "r", encoding="utf-8") as f:
        all_issues.extend(json.load(f))

out = RAW_DIR / f"{date.today().isoformat()}.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(all_issues, f, ensure_ascii=False)

print(f"Merged {len(all_issues)} issues from {len(pages)} pages → {out.name}")

for p in pages:
    p.unlink()
    print(f"  Cleaned up {p.name}")
