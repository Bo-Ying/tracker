# 02 — Collect candidates from GitHub search

Status: ready-for-agent
Blocked by: 01

Search `topic:<t> stars:>=100 fork:false archived:false` per topic, splitting star ranges whenever a query exceeds the 1,000-result cap. Respect the 30 req/min search limit; retry 5xx and secondary rate limits.

## Acceptance
- Union per column, deduplicated by repo id.
- Range splitting covered by a test with a fake client.
