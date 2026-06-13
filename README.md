# PostHog Engineering Impact Dashboard

Identifies the **5 most impactful engineers** in
[`PostHog/posthog`](https://github.com/PostHog/posthog) over the last 90 days,
for a busy engineering leader.

**🔗 Live demo: https://weaveassignment.vercel.app**

## Thesis: impact = force multiplication

The most impactful engineer isn't the one with the most commits — it's the one
who **makes the whole team faster** and whose absence would slow everyone down.

The one thing GitHub data can **cleanly prove** about this is **review &
unblocking influence**: one person measurably helping another, with names and
timestamps. So the score is built around the review graph, and we **state
honestly** that this captures the *provable* dimension of impact. Whether the
work itself matters, and who owns the hardest systems, need human context —
those are shown as context stats, never folded into the score.

## The impact score (0–100)

A blended percentile across six review-graph dimensions, each normalized to a
percentile against the active-engineer pool (≥3 authored PRs), then weighted:

| Dimension | Weight | What it captures |
|---|---|---|
| **Distinct people unblocked** | 30% | how many *different* colleagues' PRs they reviewed |
| **Review reciprocity** | 20% | reviews given ÷ reviews received (do they give back?) |
| **Substantive-review ratio** | 15% | commented/changes-requested ÷ total (not rubber-stamps) |
| **Responsiveness** | 15% | median time-to-first-review on others' PRs (inverted) |
| **Involvement** | 10% | comments left on others' PRs |
| **Review volume** | 10% | total reviews given |

**Filters:** bots are excluded everywhere (via GitHub's `__typename: Bot`);
chore & generated PRs (snapshots, lockfiles) are excluded from scoring but kept
for context counts.

### Shown as context, never scored
AI-leverage (% AI-authored PRs + tools), merge rate, merge throughput, reverts
(PRs rolled back within 48h — a rare red flag), work-type mix, and PR size.

### Considered and rejected
Cycle time (mostly review-wait latency), CI-pass rate (~constant ~88%),
closes-issues / label urgency (data too sparse), AI autonomy (null in the data).

## Architecture

```
pipeline/        Offline Python data pipeline (run once locally)
  github_client.py   GraphQL client over httpx (token from `gh` CLI)
  extract.py         Pull merged + closed-unmerged PRs, 90 days, resumable by date window
  ai_authoring.py    Detect AI tool + autonomy from PR body / commit footers
  metrics.py         Compute the six scored dimensions + context + team panel
  run.py             extract -> metrics -> frontend/public/data.json
frontend/        Static Vite + React + TS app (deployed to Vercel)
  public/data.json   Precomputed — no live API calls at view time (<1s load)
  src/pages/         Home (top 5, scatter, team panel) + EngineerDetail
  src/components/    ImpactRadar, RankRow, EffortScatter, CategoryLeaderboard,
                     AttentionPanel (where-the-work-is + chokepoints), ThemeToggle
  src/types.ts       Typed metric shapes
```

The frontend reads a **static, precomputed `public/data.json`** — Vercel just
serves the static build, so it loads in well under a second.

## Run it

```bash
# 1. Data pipeline (needs `gh auth login` or GITHUB_TOKEN)
cd pipeline && pip install -r requirements.txt && python run.py

# 2. Frontend
cd ../frontend && npm install && npm run dev      # local
npm run build                                      # production build -> dist/
```

## Tech
React + TypeScript + Vite, Recharts (radar + scatter), Python + httpx + GitHub
GraphQL. Black/orange theme, dark by default with a light toggle.
