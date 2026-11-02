# 01 — Project scaffold and config

Status: ready-for-agent

Python package `tracker` (Python ≥ 3.11, uv locally, pip in CI), `config.toml` holding columns, topics, thresholds, exclusion rules, blocklist and the translation model. Pytest set up.

## Acceptance
- `uv run pytest` runs.
- Config loads into typed objects; invalid config fails loudly.

## Comments

- 2026-11-02: implemented in 78726b1; tests pass (31). 07 still needs its first run on GitHub.
