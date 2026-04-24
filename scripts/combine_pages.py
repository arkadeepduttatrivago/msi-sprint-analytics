"""Combine paginated raw MCP responses into a single file.

Reads tasks/ad_hocs/msi-jira-analytics/data/raw/<date>_pageN.json files
and merges their `issues` arrays into a single raw file:
<date>.json with {"issues": [...]}.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW_DIR = BASE / "data" / "raw"


def main():
    if len(sys.argv) < 2:
        print("Usage: python combine_pages.py <date>")
        sys.exit(1)
    date = sys.argv[1]
    page_files = sorted(RAW_DIR.glob(f"{date}_page*.json"))
    if not page_files:
        print(f"ERROR: No page files matching {date}_page*.json")
        sys.exit(1)

    all_issues = []
    for pf in page_files:
        with open(pf, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            issues = data
        else:
            issues = data.get("issues", [])
        print(f"  {pf.name}: {len(issues)} issues")
        all_issues.extend(issues)

    out = RAW_DIR / f"{date}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"issues": all_issues}, f, indent=2, ensure_ascii=False)
    size_kb = out.stat().st_size / 1024
    print(f"\nCombined {len(all_issues)} issues -> {out.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
