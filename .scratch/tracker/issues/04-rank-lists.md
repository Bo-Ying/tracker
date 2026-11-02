# 04 — Rank Hot and Rising lists

Status: ready-for-agent
Blocked by: 02, 03

Hot: top 10 by gain over `max(now−30d, earliest snapshot)`. Rising: top 10 by 7-day growth %, stars ≥ 500, start stars > 0. Exclusions (resource collections, blocklist). Rank change vs previous issue, 🆕, duplicate badges. Issue JSON written to `data/issues/<YYYY-Www>.json`; baseline issue on first run.

## Acceptance
- Tests for each rule above.

## Comments

- 2026-11-02: implemented in 78726b1; tests pass (31). 07 still needs its first run on GitHub.
