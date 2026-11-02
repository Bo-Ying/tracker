"""Render data/issues/*.json into a static site under _site/."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Config
from .snapshots import parse_time

HERE = Path(__file__).resolve().parent
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def date_range_en(start: datetime, end: datetime) -> str:
    a = f"{MONTHS[start.month - 1]} {start.day}"
    b = f"{MONTHS[end.month - 1]} {end.day}, {end.year}"
    if start.year != end.year:
        a += f", {start.year}"
    return f"{a} – {b}"


def date_range_zh(start: datetime, end: datetime) -> str:
    a = f"{start.year}年{start.month}月{start.day}日"
    b = f"{end.month}月{end.day}日" if start.year == end.year else f"{end.year}年{end.month}月{end.day}日"
    return f"{a} – {b}"


def date_en(t: datetime) -> str:
    return f"{MONTHS[t.month - 1]} {t.day}, {t.year}"


def date_zh(t: datetime) -> str:
    return f"{t.year}年{t.month}月{t.day}日"


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(HERE / "templates"),
                      autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.filters["num"] = lambda n: f"{int(n):,}"
    env.filters["signed"] = lambda n: f"+{int(n):,}" if n >= 0 else f"{int(n):,}"
    env.filters["pct"] = lambda p: f"+{p:,.0f}%" if p >= 10 else f"+{p:.1f}%"
    return env


def _decorate(issue: dict, translations: dict[str, str]) -> dict:
    """Add display-only fields (formatted dates, Chinese descriptions)."""
    w = issue["window"]
    end = parse_time(w["end"])
    rising_start = parse_time(w["rising_start"])
    issue = {**issue}
    issue["range_en"] = date_range_en(rising_start, end)
    issue["range_zh"] = date_range_zh(rising_start, end)
    first = parse_time(issue["first_rankings_at"])
    issue["first_en"], issue["first_zh"] = date_en(first), date_zh(first)
    issue["generated_en"] = date_en(parse_time(issue["generated_at"]))
    issue["generated_zh"] = date_zh(parse_time(issue["generated_at"]))
    for col in issue["columns"]:
        for lst in ("hot", "rising"):
            for e in col[lst]:
                e["description_zh"] = translations.get(e["description"]) or e.get("description_zh")
    return issue


def load_issues(issues_dir: Path) -> list[dict]:
    issues = [json.loads(p.read_text()) for p in issues_dir.glob("*.json")]
    return sorted(issues, key=lambda i: i["generated_at"], reverse=True)


def build_site(config: Config, issues_dir: Path, translations: dict[str, str], out: Path) -> list[Path]:
    issues = [_decorate(i, translations) for i in load_issues(issues_dir)]
    if out.exists():
        shutil.rmtree(out)
    (out / "static").mkdir(parents=True)
    for f in (HERE / "static").iterdir():
        shutil.copy(f, out / "static" / f.name)

    env = _env()
    columns_meta = {c.key: c for c in config.columns}
    common = {"config": config, "columns_meta": columns_meta, "latest": issues[0] if issues else None}
    written = []

    def write(path: Path, template: str, **ctx) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(env.get_template(template).render(**common, **ctx))
        written.append(path)

    if not issues:
        write(out / "index.html", "empty.html", root="")
        return written
    write(out / "index.html", "issue.html", root="", issue=issues[0], is_latest=True)
    for issue in issues:
        write(out / "issues" / issue["label"] / "index.html", "issue.html",
              root="../../", issue=issue, is_latest=issue is issues[0])
    write(out / "archive" / "index.html", "archive.html", root="../", issues=issues)
    return written
