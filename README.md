# MSI OKR Sprint Analytics

Sprint velocity, burndown, per-person, team, and initiative dashboards for the MSI Jira board.

**No Jira credentials needed at runtime.** Data is pre-fetched and stored in `data/sprints.json`.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How Data Gets Updated

### Option A: Automated (GitHub Actions)

A scheduled workflow runs twice per week:
- **Monday 09:00 CET** (sprint start)
- **Friday 18:00 CET** (sprint end)

It fetches all MSI OKR issues from Jira, rebuilds `data/sprints.json`, and commits the update. You can also trigger it manually from the Actions tab.

**Required secrets** (set in repo Settings > Secrets):

| Secret | Value |
|--------|-------|
| `JIRA_CLOUD_ID` | `c1d8debe-4d98-460f-81b3-caee34642ac8` |
| `JIRA_EMAIL` | Your Atlassian email |
| `JIRA_API_TOKEN` | [Create one](https://id.atlassian.com/manage-profile/security/api-tokens) |

### Option B: Manual (trv-OS / Cursor)

1. Open Cursor in the `trv-os` workspace
2. Run `/update-sprint-analytics` — Robert fetches data from Jira via MCP
3. Data is saved to `data/sprints.json` (old sprint data is preserved)
4. Run `streamlit run app.py` to view, or push to trigger Streamlit Cloud redeploy

## Deploy

### Streamlit Cloud (recommended)

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect this repo, select `app.py`
3. Share the URL — no credentials needed, data is baked in
4. Auto-redeploys when `data/sprints.json` changes on `main`

### Docker (nginx static)

```bash
docker build -f Dockerfile.nginx -t msi-sprint-analytics .
docker run -p 80:80 msi-sprint-analytics
```

### trivago internal deploy

```bash
docker build -f Dockerfile.nginx -t msi-sprint-analytics:latest .
docker tag msi-sprint-analytics:latest \
  cr.internal.prod.europe-dus1.tools.trv.cloud/msi-sprint-analytics:latest
docker push \
  cr.internal.prod.europe-dus1.tools.trv.cloud/msi-sprint-analytics:latest
```

Then deploy via `score.yaml` using the trivago Deploy MCP.

## Dashboard Pages

| Page | What it shows |
|------|---------------|
| Sprint Overview | KPI cards, status donut, issue table |
| Velocity Trends | Velocity bars, 3-sprint rolling avg |
| Per-Person | SP by person per sprint |
| Team Breakdown | SP by team (OPS / EXP / Brand & CIM) |
| Initiative Progress | Epic/KR completion %, milestones |
| Sprint Completion | Carry-over SP, progress vs 80% target |

## Architecture

```
Jira (board 7527 / label MSI_OKRS_2026)
  → scripts/fetch_jira.py  (REST API, used by GitHub Action)
  — or —
  → Atlassian MCP           (used by /update-sprint-analytics)
  → data/raw/<date>.json
  → scripts/build_data.py
  → data/sprints.json
  → Streamlit app (local) or nginx + static HTML (deployed)
```

## Documentation

- [How It Works (Confluence)](https://trivago.atlassian.net/wiki/spaces/Marketing/pages/4684022271)
- Skill file: `.cursor/skills/msi-jira-analytics/SKILL.md`
