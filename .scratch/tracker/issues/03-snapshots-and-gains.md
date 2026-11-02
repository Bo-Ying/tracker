# 03 — Snapshots, interpolation and gains

Status: ready-for-agent
Blocked by: 01

Store `data/snapshots/<timestamp>.json` (`{id: stars}`). `stars_at(repo, t)` with interpolation, created-after-snapshot = 0, unknown otherwise, 1-day clamp before the earliest snapshot.

## Acceptance
- Unit tests for interpolation, missing repos, clamping, cold start.
