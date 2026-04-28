# MSI OKR Sprint Analytics

Static HTML dashboard for MSI sprint tracking — velocity, team breakdown, per-person, initiative progress.

**No backend, no credentials at runtime.** The dashboard is a single `index.html` that loads `data/sprints.json` via `fetch()`. Hosted on GitHub Pages.

## Live Dashboard

**URL:** `https://arkadeepduttatrivago.github.io/msi-sprint-analytics/`

(Enable GitHub Pages in repo Settings > Pages > Source: GitHub Actions)

## How Data Gets Updated

### Automated (GitHub Actions)

A scheduled workflow checks multiple times before **09:00 Europe/Berlin**
to keep the dashboard fresh. It runs at `06:15`, `06:35`, `06:55`,
`07:15`, `07:35`, and `07:55` UTC. A freshness guard lets the first
successful run per day update the data; later scheduled runs exit cleanly.

For out-of-band manual refreshes (e.g. before a stakeholder review), use the trv-OS command `/git-update-sprint-numbers` from Cursor — it fetches Jira, rebuilds `data/sprints.json`, and pushes to `main` so Pages redeploys immediately.

It fetches Jira data via REST API, rebuilds `data/sprints.json`, commits the update, and redeploys GitHub Pages.

Trigger manually anytime from the [Actions tab](../../actions).

**Required secrets** (repo Settings > Secrets):

| Secret | Value |
|--------|-------|
| `JIRA_CLOUD_ID` | `c1d8debe-4d98-460f-81b3-caee34642ac8` |
| `JIRA_EMAIL` | Your Atlassian email |
| `JIRA_API_TOKEN` | [Create one](https://id.atlassian.com/manage-profile/security/api-tokens) |

### Manual (trv-OS / Cursor)

1. Run `/update-sprint-analytics` in Cursor
2. Push `data/sprints.json` — GitHub Pages auto-redeploys

## Local Development

```bash
# Serve locally (any static server)
python -m http.server 8000
# Open http://localhost:8000
```

Or with Streamlit (full interactive version):
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Dashboard Tabs

| Tab | What it shows |
|-----|---------------|
| Sprint Overview | KPI cards, status donut, issue table |
| Velocity Trends | Velocity bars, 3-sprint rolling avg |
| Per-Person | SP by person per sprint |
| Team Breakdown | SP by team (OPS / EXP / Brand & CIM) |
| Initiative Progress | Epic/KR completion %, milestones |
| Sprint Completion | Carry-over SP, progress vs 80% target |

## Architecture

```
Jira (board 7527 / label MSI_OKRS_2026)
  → scripts/fetch_jira.py  (REST API, GitHub Action cron)
  → data/raw/<date>.json
  → scripts/build_data.py
  → data/sprints.json
  → index.html (GitHub Pages)
```

## Documentation

- [How It Works (Confluence)](https://trivago.atlassian.net/wiki/spaces/Marketing/pages/4684022271)
