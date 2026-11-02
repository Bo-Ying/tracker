# 03 — Snapshots, interpolation and gains

Status: ready-for-agent
Blocked by: 01

Store `data/snapshots/<timestamp>.json` (`{id: stars}`). `stars_at(repo, t)` with interpolation, created-after-snapshot = 0, unknown otherwise, 1-day clamp before the earliest snapshot.

## Acceptance
- Unit tests for interpolation, missing repos, clamping, cold start.

## Comments

- 2026-11-02: implemented in 78726b1; tests pass (31). 07 still needs its first run on GitHub.
