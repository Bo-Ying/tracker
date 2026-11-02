# Spec: tracker — weekly GitHub trending for AI Agents & Quant

Status: needs-triage

A static website, rebuilt weekly, that ranks GitHub repositories in two columns — **AI Agents** and **Quant** — each with two leaderboards.

## Leaderboards

Each column has two lists of up to 10 repos:

- **Hot**: most stars gained in the rolling last 30 days (absolute count).
- **Rising**: highest 7-day star growth percentage, only repos with total stars ≥ 500 (threshold configurable).

If fewer than 10 repos qualify, show what qualifies; never pad.

No de-duplication: a repo may appear in both lists of a column and in both columns. A repo appearing elsewhere gets a badge (e.g. "also in Hot", "also in Quant").

## Classification

- A repo belongs to a column if it has any of that column's GitHub topics (config file):
  - AI Agents: `ai-agent`, `ai-agents`, `agent`, `agents`, `llm-agent`, `autonomous-agents`, `multi-agent`, `agentic-ai`
  - Quant: `quant`, `quantitative-finance`, `quantitative-trading`, `algorithmic-trading`, `backtesting`, `trading-bot`, `trading-strategies`
- Candidate pool: matching repos with total stars ≥ 100.
- Excluded: forks, archived repos, resource collections (name starts with `awesome-`, or topics like `awesome-list`, `tutorial`, `course`; rules in config).
- Manual blocklist in config.

## Data

- GitHub no longer serves stargazer lists (REST `/stargazers` returns 404, GraphQL returns no edges — verified 2026-11-02), so there is **no historical backfill**. Star gains come only from our own snapshots.
- Every run snapshots total stars for the whole candidate pool (keyed by numeric repo id, so renames don't break history), stored as JSON in the repo.
- `stars_at(repo, t)` linearly interpolates between the two snapshots bracketing `t` (30 days is not a multiple of the 7-day cadence). A repo missing from a snapshot counts as 0 if it was created after that snapshot, otherwise its value is unknown and it is left out of that list. A target time up to 1 day before the earliest snapshot clamps to it (cron jitter).
- **Cold start**:
  - First run: baseline snapshot only; the page says tracking has started and when the first rankings appear.
  - Rising needs a snapshot ~7 days old, so it appears from the second run.
  - Hot uses `max(now − 30d, earliest snapshot)` as its window start and labels the actual length ("last 7 / 14 / 21 days, building up to 30") until 30 days of history exist.
- Rank change is computed against the previous issue's list; repos not in it get 🆕.

## Schedule & failure handling

- GitHub Actions cron every Monday 00:00 UTC (08:00 Beijing), plus `workflow_dispatch` for manual runs.
- Each issue is labelled with its window in UTC, e.g. `2026-W45 · Oct 27 – Nov 3, 2026 (UTC)`.
- Individual API requests retry with backoff. If the run still fails, abort without publishing; the site keeps the previous issue and GitHub's failure email notifies the owner.
- Translation failure never blocks publishing: fall back to the English description.
  - Transient errors (network, rate limit, 5xx, refusal): retry, then fall back silently.
  - Configuration errors (missing/invalid key, model not found — e.g. a retired model — billing/credit exhausted): publish with English, then mark the workflow run failed so GitHub emails the owner. The model id lives in `config.toml`, so switching models is a one-line change.

## Page

- UI language English by default; EN / 中文 toggle top-right, choice remembered in the browser. UI strings are hand-written in both languages.
- Descriptions are translated to Chinese at build time with Claude Haiku 5.5 (`claude-haiku-5-5`), keeping technical terms and project names untranslated. Translations are cached keyed by description text; only new/changed descriptions are translated. API key in GitHub Secrets.
- Card fields: rank, `owner/repo` (linked), description, primary language, total stars, list metric (Hot: +30-day stars; Rising: +7-day % and absolute), rank change (↑n / ↓n / 🆕), duplicate badges.
- Layout: header (title, issue date, language toggle); two columns stacked vertically (AI Agents, Quant); inside each, Hot and Rising side by side on desktop, stacked on mobile. Card style; dark mode follows the system.
- Archive: every weekly issue is kept at `/<YYYY-Www>/`; the home page shows the latest; an archive page lists past issues.

## Tech & hosting

- Python + Jinja2 → plain static HTML, minimal vanilla JS (language toggle).
- Public GitHub repo `tracker`, served by GitHub Pages at `https://<user>.github.io/tracker/`.

## Owner prerequisites

1. Install `gh` and log in; set git `user.name` / `user.email`.
2. Create the public repo `tracker` and push.
3. Anthropic API key → repo secret `ANTHROPIC_API_KEY`.
4. Enable GitHub Pages for the repo (source: GitHub Actions).
