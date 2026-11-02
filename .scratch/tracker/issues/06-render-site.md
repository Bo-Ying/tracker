# 06 — Render the static site

Status: ready-for-agent
Blocked by: 04

Jinja2 → `_site/`: latest issue at `/`, every issue at `/issues/<label>/`, archive at `/archive/`. EN/中文 toggle (remembered, no flash), card layout, two columns stacked, lists side by side on desktop, dark mode via system preference. Relative links so the site works under `/tracker/`.

## Acceptance
- Build from fixture issues produces all pages; smoke test checks key content.

## Comments

- 2026-11-02: implemented in 78726b1; tests pass (31). 07 still needs its first run on GitHub.
