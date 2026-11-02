import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tracker.config import load_config
from tracker.github import Repo
from tracker.rank import build_issue
from tracker.render import build_site, date_range_en, date_range_zh
from tracker.snapshots import History, Snapshot

CONFIG = load_config(Path(__file__).resolve().parent.parent / "config.toml")
T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)
OLD = "2024-01-01T00:00:00Z"


def repo(id, stars, desc):
    return Repo(id=id, full_name=f"o/r{id}", name=f"r{id}", url=f"https://github.com/o/r{id}",
                description=desc, language="Python", stars=stars, topics=("ai-agent",),
                created_at=OLD, pushed_at=OLD)


def write_issues(tmp_path):
    issues = tmp_path / "issues"
    issues.mkdir()
    repos = {1: repo(1, 1500, "An <agent> framework"), 2: repo(2, 1100, "Backtesting engine")}
    snaps = [Snapshot(T0, {1: 1000, 2: 1000})]
    base = build_issue(CONFIG, repos, {"agents": {1, 2}, "quant": {2}}, History(snaps), T0, None)
    snaps.append(Snapshot(T0 + timedelta(days=7), {1: 1500, 2: 1100}))
    week2 = build_issue(CONFIG, repos, {"agents": {1, 2}, "quant": {2}}, History(snaps),
                        T0 + timedelta(days=7), base)
    for issue in (base, week2):
        (issues / f"{issue['label']}.json").write_text(json.dumps(issue))
    return issues


def test_build_site_pages(tmp_path):
    out = tmp_path / "_site"
    written = build_site(CONFIG, write_issues(tmp_path), {"An <agent> framework": "一个 agent 框架"}, out)
    rel = sorted(str(p.relative_to(out)) for p in written)
    assert rel == ["archive/index.html", "index.html",
                   "issues/2026-W44/index.html", "issues/2026-W45/index.html"]
    assert (out / "static" / "style.css").exists()

    home = (out / "index.html").read_text()
    assert "o/</span><span class=\"name\">r1" in home
    assert "An &lt;agent&gt; framework" in home  # escaped
    assert "一个 agent 框架" in home
    assert "+500" in home and "+50%" in home
    assert "building up to 30" in home
    assert 'href="static/style.css"' in home

    baseline = (out / "issues" / "2026-W44" / "index.html").read_text()
    assert "Tracking has started" in baseline
    assert 'href="../../static/style.css"' in baseline


def test_build_site_with_no_issues(tmp_path):
    (tmp_path / "issues").mkdir()
    written = build_site(CONFIG, tmp_path / "issues", {}, tmp_path / "_site")
    assert [p.name for p in written] == ["index.html"]


def test_date_ranges():
    a, b = datetime(2026, 12, 28, tzinfo=timezone.utc), datetime(2027, 1, 4, tzinfo=timezone.utc)
    assert date_range_en(a, b) == "Dec 28, 2026 – Jan 4, 2027"
    assert date_range_zh(a, b) == "2026年12月28日 – 2027年1月4日"
