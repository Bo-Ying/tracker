# Tracker

Weekly GitHub trending for **AI Agents** and **Quant** repositories, published at
<https://bo-ying.github.io/tracker/>.

Each column has two lists of 10:

- **Hot**: most stars gained in the last 30 days.
- **Rising**: fastest 7-day star growth (%), among repos with 500+ stars.

## How it works

1. Every Monday 00:00 UTC, GitHub Actions searches GitHub for repos tagged with the
   topics in [`config.toml`](config.toml) (100+ stars, no forks or archived repos).
2. It saves a snapshot of every candidate's star count in `data/snapshots/`.
   GitHub doesn't publish when stars were given, so gains are differences between
   these snapshots; the 30-day baseline is interpolated between weekly snapshots.
3. It ranks the lists, translates new descriptions into Chinese with Claude
   (cached in `data/translations.json`), and writes `data/issues/<YYYY-Www>.json`.
4. It commits the data and deploys the static site to GitHub Pages.

Until 30 days of snapshots exist, Hot covers the history available so far and says so.

## Configuration

Edit [`config.toml`](config.toml): topics per column, thresholds, the exclusion
rules for resource lists, a manual blocklist, and the translation model.

If translation fails because of configuration (missing or invalid
`ANTHROPIC_API_KEY`, no credit, retired model), the site still publishes with
English descriptions and the workflow run is marked failed, so GitHub emails you.

## Local development

```sh
uv sync
uv run pytest
uv run python -m tracker update --skip-translate   # uses `gh auth token`
uv run python -m tracker build                     # writes _site/
open _site/index.html
```
