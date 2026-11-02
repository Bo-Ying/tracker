# 01 — Project scaffold and config

Status: ready-for-agent

Python package `tracker` (Python ≥ 3.11, uv locally, pip in CI), `config.toml` holding columns, topics, thresholds, exclusion rules, blocklist and the translation model. Pytest set up.

## Acceptance
- `uv run pytest` runs.
- Config loads into typed objects; invalid config fails loudly.
