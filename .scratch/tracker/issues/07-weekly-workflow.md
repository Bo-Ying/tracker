# 07 — Weekly GitHub Actions workflow

Status: ready-for-agent
Blocked by: 05, 06

Cron `0 0 * * 1` + `workflow_dispatch`. Update → commit data → build → deploy to Pages → fail the run if a translation config error was flagged. Concurrency guard.

## Acceptance
- Workflow file lints; first manual run on GitHub succeeds.

## Comments

- 2026-11-02: implemented in 78726b1; tests pass (31). 07 still needs its first run on GitHub.
- 2026-11-02: first manual run succeeded (run 41466551344, 6m49s); site live.
