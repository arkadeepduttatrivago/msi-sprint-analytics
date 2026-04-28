"""Fetch MSI OKR issues from Jira REST API and save to data/raw/.

Used by the GitHub Action (no MCP available in CI).
Requires environment variables: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN.
Optional: JQL_OVERRIDE to use a custom query.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
RAW_DIR = BASE / "data" / "raw"

CLOUD_ID = os.environ.get("JIRA_CLOUD_ID", "")
EMAIL = os.environ.get("JIRA_EMAIL", "")
TOKEN = os.environ.get("JIRA_API_TOKEN", "")
BASE_URL = os.environ.get(
    "JIRA_BASE_URL",
    f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3"
    if CLOUD_ID else ""
)

DEFAULT_JQL = (
    "project = MSI AND labels = MSI_OKRS_2026 ORDER BY key ASC"
)

FIELDS = [
    "summary", "status", "assignee", "issuetype",
    "customfield_10033", "customfield_10016",
    "customfield_10020", "sprint",
    "parent", "labels", "duedate", "resolutiondate",
]


def fetch_all_issues(jql: str) -> list[dict]:
    if not BASE_URL or not EMAIL or not TOKEN:
        print("ERROR: JIRA_BASE_URL, JIRA_EMAIL, and "
              "JIRA_API_TOKEN must be set.")
        sys.exit(1)

    # Atlassian removed /rest/api/3/search; enhanced search now lives here.
    url = f"{BASE_URL}/search/jql"
    auth = (EMAIL, TOKEN)
    next_page_token = None
    max_results = 100
    all_issues: list[dict] = []

    while True:
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": ",".join(FIELDS),
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token
        resp = requests.get(url, params=params, auth=auth, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        issues = data.get("issues", [])
        all_issues.extend(issues)
        print(f"  Fetched {len(issues)} issues "
              f"(total so far: {len(all_issues)})")

        next_page_token = data.get("nextPageToken")
        if data.get("isLast", False) or not next_page_token:
            break

    return all_issues


def main():
    jql = os.environ.get("JQL_OVERRIDE", "").strip() or DEFAULT_JQL
    print(f"Fetching issues with JQL: {jql}")

    issues = fetch_all_issues(jql)
    print(f"Total issues fetched: {len(issues)}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_file = RAW_DIR / f"{today}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"issues": issues}, f, indent=2, ensure_ascii=False)

    print(f"Saved to {out_file} "
          f"({out_file.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
