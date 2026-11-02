# 05 — Translate descriptions with Claude

Status: ready-for-agent
Blocked by: 04

Batch-translate uncached descriptions with `claude-haiku-5-5` (structured JSON output, low effort), cache in `data/translations.json`. Transient errors → English fallback; config errors → English fallback + flag the run as failed.

## Acceptance
- Tests with a fake client: cache hits skip the API; each error class goes to the right bucket.
