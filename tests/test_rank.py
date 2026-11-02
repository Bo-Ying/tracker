from datetime import datetime, timedelta, timezone
from pathlib import Path

from tracker.config import load_config
from tracker.github import Repo
from tracker.rank import build_issue, hot_list, is_excluded, issue_label, rising_list
from tracker.snapshots import History, Snapshot

T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)
OLD = "2024-01-01T00:00:00Z"
CONFIG = load_config(Path(__file__).resolve().parent.parent / "config.toml")


def day(n: float) -> datetime:
    return T0 + timedelta(days=n)


def repo(id, stars, name=None, created=OLD, topics=("ai-agent",)) -> Repo:
    name = name or f"repo{id}"
    return Repo(id=id, full_name=f"o/{name}", name=name, url=f"https://github.com/o/{name}",
                description=f"desc {id}", language="Python", stars=stars, topics=tuple(topics),
                created_at=created, pushed_at=OLD)


def test_issue_label_is_week_covered():
    assert issue_label(datetime(2026, 11, 2, tzinfo=timezone.utc)) == "2026-W44"
    assert issue_label(datetime(2026, 11, 9, 0, 20, tzinfo=timezone.utc)) == "2026-W45"


def test_exclusions():
    ex = CONFIG.exclude
    assert is_excluded(repo(1, 900, name="awesome-ai-agents"), ex)
    assert is_excluded(repo(2, 900, topics=("ai-agent", "tutorial")), ex)
    assert not is_excluded(repo(3, 900), ex)


def test_hot_ranks_by_absolute_gain_and_includes_new_repos():
    h = History([Snapshot(day(0), {1: 10_000, 2: 500}), Snapshot(day(30), {})])
    pool = [repo(1, 13_000), repo(2, 900), repo(3, 2_000, created="2026-11-20T00:00:00Z")]
    out = hot_list(pool, h, day(0), 10)
    assert [(e.id, e.gain) for e in out] == [(1, 3000), (3, 2000), (2, 400)]


def test_rising_ranks_by_percentage_with_star_floor():
    h = History([Snapshot(day(0), {1: 10_000, 2: 400, 3: 100})])
    pool = [repo(1, 13_000), repo(2, 800), repo(3, 450)]  # repo 3 is below 500 stars
    out = rising_list(pool, h, day(0), 10, min_stars=500)
    assert [(e.id, e.growth_pct) for e in out] == [(2, 100.0), (1, 30.0)]


def test_rising_skips_brand_new_repos():
    h = History([Snapshot(day(0), {})])
    out = rising_list([repo(1, 900, created="2026-11-05T00:00:00Z")], h, day(0), 10, 500)
    assert out == []


def _issue(snaps, repos, now, previous=None):
    all_repos = {r.id: r for r in repos}
    return build_issue(CONFIG, all_repos, {"agents": set(all_repos), "quant": {2} & set(all_repos)},
                       History(snaps), now, previous)


def test_first_run_is_baseline():
    issue = _issue([Snapshot(day(0), {1: 100})], [repo(1, 100)], day(0))
    assert issue["status"] == "baseline"
    assert issue["first_rankings_at"] == "2026-11-09T00:00:00Z"
    assert all(not c["hot"] and not c["rising"] for c in issue["columns"])


def test_second_week_hot_window_is_seven_days():
    snaps = [Snapshot(day(0), {1: 1000, 2: 1000}), Snapshot(day(7), {1: 1500, 2: 1100})]
    issue = _issue(snaps, [repo(1, 1500), repo(2, 1100)], day(7))
    assert issue["status"] == "ok"
    assert issue["window"]["hot_days"] == 7
    agents = issue["columns"][0]
    assert [e["id"] for e in agents["hot"]] == [1, 2]
    assert [e["id"] for e in agents["rising"]] == [1, 2]


def test_full_history_uses_thirty_days():
    snaps = [Snapshot(day(7 * i), {1: 1000 + 100 * i}) for i in range(6)]
    issue = _issue(snaps, [repo(1, 1500)], day(35))
    assert issue["window"]["hot_days"] == 30
    hot = issue["columns"][0]["hot"]
    assert hot[0]["gain"] == round(1500 - (1000 + 100 * 5 / 7))


def test_rank_change_and_new_badge():
    snaps = [Snapshot(day(0), {1: 1000, 2: 1000}), Snapshot(day(7), {1: 1500, 2: 1100})]
    previous = {"columns": [{"key": "agents", "hot": [{"id": 2, "rank": 1}], "rising": []}]}
    issue = _issue(snaps, [repo(1, 1500), repo(2, 1100)], day(7), previous)
    hot = issue["columns"][0]["hot"]
    assert (hot[0]["id"], hot[0]["is_new"], hot[0]["prev_rank"]) == (1, True, None)
    assert (hot[1]["id"], hot[1]["is_new"], hot[1]["prev_rank"]) == (2, False, 1)


def test_duplicate_badges():
    snaps = [Snapshot(day(0), {1: 1000, 2: 1000}), Snapshot(day(7), {1: 1500, 2: 1100})]
    issue = _issue(snaps, [repo(1, 1500), repo(2, 1100)], day(7))
    agents, quant = issue["columns"]
    r2 = next(e for e in agents["hot"] if e["id"] == 2)
    assert r2["also_in_list"] is True
    assert r2["also_in_columns"] == ["quant"]
    assert quant["hot"][0]["also_in_columns"] == ["agents"]
