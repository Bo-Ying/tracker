"""Turn the candidate pool and star history into one weekly issue."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from .config import Config, Exclude
from .github import Repo
from .snapshots import History, format_time, parse_time

DAY = timedelta(days=1)
# A list needs at least this much history to be published.
MIN_WINDOW = timedelta(days=6)


@dataclass
class Entry:
    id: int
    full_name: str
    url: str
    description: str
    language: str | None
    stars: int
    gain: int
    growth_pct: float | None = None
    rank: int = 0
    prev_rank: int | None = None
    is_new: bool = False
    also_in_list: bool = False
    also_in_columns: list[str] = field(default_factory=list)
    description_zh: str | None = None


def issue_label(end: datetime) -> str:
    """ISO week of the 7 days the issue covers, e.g. '2026-W44'."""
    year, week, _ = (end - timedelta(days=7)).isocalendar()
    return f"{year}-W{week:02d}"


def is_excluded(repo: Repo, ex: Exclude) -> bool:
    name = repo.name.lower()
    if any(name.startswith(p) for p in ex.name_prefixes):
        return True
    if ex.topics.intersection(t.lower() for t in repo.topics):
        return True
    return repo.full_name.lower() in ex.repos


def _gain(history: History, repo: Repo, start: datetime) -> tuple[int, float] | None:
    before = history.stars_at(repo.id, parse_time(repo.created_at), start)
    if before is None:
        return None
    return round(repo.stars - before), before


def hot_list(repos: list[Repo], history: History, start: datetime, size: int) -> list[Entry]:
    scored = []
    for r in repos:
        g = _gain(history, r, start)
        if g is not None and g[0] > 0:
            scored.append((g[0], r))
    scored.sort(key=lambda x: (-x[0], -x[1].stars, x[1].full_name))
    return [_entry(r, gain) for gain, r in scored[:size]]


def rising_list(repos: list[Repo], history: History, start: datetime,
                size: int, min_stars: int) -> list[Entry]:
    scored = []
    for r in repos:
        if r.stars < min_stars:
            continue
        g = _gain(history, r, start)
        if g is None or g[0] <= 0 or g[1] < 1:
            continue  # brand-new repos have no meaningful percentage; Hot covers them
        gain, before = g
        scored.append((gain / before * 100, gain, r))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2].full_name))
    out = []
    for pct, gain, r in scored[:size]:
        e = _entry(r, gain)
        e.growth_pct = round(pct, 1)
        out.append(e)
    return out


def _entry(r: Repo, gain: int) -> Entry:
    return Entry(id=r.id, full_name=r.full_name, url=r.url, description=r.description,
                 language=r.language, stars=r.stars, gain=gain)


def _apply_ranks(entries: list[Entry], prev: list[dict] | None) -> None:
    prev_ranks = {e["id"]: e["rank"] for e in prev or []}
    for i, e in enumerate(entries, 1):
        e.rank = i
        e.prev_rank = prev_ranks.get(e.id)
        e.is_new = prev is not None and e.prev_rank is None


def build_issue(config: Config, all_repos: dict[int, Repo], by_column: dict[str, set[int]],
                history: History, now: datetime, previous: dict | None) -> dict:
    rising_start = now - config.rising_days * DAY
    hot_start = max(now - config.hot_days * DAY, history.earliest)
    hot_window = now - hot_start
    rising_ok = history.covers(rising_start) and now - history.earliest >= MIN_WINDOW
    hot_ok = hot_window >= MIN_WINDOW

    prev_cols = {c["key"]: c for c in (previous or {}).get("columns", [])}
    columns = []
    for col in config.columns:
        pool = [all_repos[i] for i in by_column.get(col.key, ())
                if not is_excluded(all_repos[i], config.exclude)]
        hot = hot_list(pool, history, hot_start, config.list_size) if hot_ok else []
        rising = (rising_list(pool, history, rising_start, config.list_size,
                              config.min_stars_rising) if rising_ok else [])
        prev = prev_cols.get(col.key, {})
        _apply_ranks(hot, prev.get("hot") if previous else None)
        _apply_ranks(rising, prev.get("rising") if previous else None)
        columns.append({"key": col.key, "name_en": col.name_en, "name_zh": col.name_zh,
                        "hot": hot, "rising": rising})

    _mark_duplicates(columns)
    hot_days = round(hot_window / DAY)
    return {
        "label": issue_label(now),
        "generated_at": format_time(now),
        "status": "ok" if (hot_ok or rising_ok) else "baseline",
        "window": {
            "end": format_time(now),
            "hot_start": format_time(hot_start),
            "hot_days": hot_days if hot_ok else 0,
            "hot_target_days": config.hot_days,
            "rising_start": format_time(rising_start),
            "rising_days": config.rising_days if rising_ok else 0,
        },
        "first_rankings_at": format_time(history.earliest + config.rising_days * DAY),
        "columns": [
            {**c, "hot": [asdict(e) for e in c["hot"]], "rising": [asdict(e) for e in c["rising"]]}
            for c in columns
        ],
    }


def _mark_duplicates(columns: list[dict]) -> None:
    in_column: dict[int, set[str]] = {}
    for c in columns:
        for e in c["hot"] + c["rising"]:
            in_column.setdefault(e.id, set()).add(c["key"])
    for c in columns:
        hot_ids = {e.id for e in c["hot"]}
        rising_ids = {e.id for e in c["rising"]}
        for lst, other in ((c["hot"], rising_ids), (c["rising"], hot_ids)):
            for e in lst:
                e.also_in_list = e.id in other
                e.also_in_columns = sorted(in_column[e.id] - {c["key"]})
