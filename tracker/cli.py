"""Command line: `python -m tracker update` and `python -m tracker build`."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import ROOT, load_config
from .github import GitHubSearch, collect
from .rank import LISTS, build_issue, issue_label
from .render import build_site
from .snapshots import History, Snapshot, SnapshotStore
from .translate import TranslationCache, translate_all

DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
ISSUES = DATA / "issues"
TRANSLATIONS = DATA / "translations.json"
SITE = ROOT / "_site"
# Created when translation hit a configuration error; the workflow fails on it
# after the site has been deployed.
TRANSLATION_FLAG = ROOT / "translation_error.txt"

log = logging.getLogger("tracker")


def github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        return subprocess.run(["gh", "auth", "token"], check=True, capture_output=True,
                              text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sys.exit("No GitHub token: set GITHUB_TOKEN or log in with `gh auth login`.")


def previous_issue(label: str) -> dict | None:
    candidates = []
    for path in ISSUES.glob("*.json"):
        issue = json.loads(path.read_text())
        if issue["label"] != label and issue.get("status") == "ok":
            candidates.append(issue)
    return max(candidates, key=lambda i: i["generated_at"], default=None)


def summary(text: str) -> None:
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(text + "\n")


def cmd_update(args: argparse.Namespace) -> None:
    config = load_config()
    now = datetime.now(timezone.utc).replace(microsecond=0)

    client = GitHubSearch(github_token())
    topics = {c.key: c.topics for c in config.columns}
    all_repos, by_column = collect(client, topics, config.min_stars_candidate)
    if not all_repos:
        sys.exit("GitHub search returned no repositories; refusing to write an empty snapshot.")
    log.info("collected %d repos", len(all_repos))

    store = SnapshotStore(SNAPSHOTS)
    snapshots = store.load_all()
    if snapshots:
        last = len(snapshots[-1].stars)
        if len(all_repos) < last * 0.5:
            sys.exit(f"Candidate pool shrank from {last} to {len(all_repos)} repos; "
                     "looks like a GitHub API problem, not publishing.")
    snap = Snapshot(now, {r.id: r.stars for r in all_repos.values()})
    store.save(snap)
    history = History(snapshots + [snap])

    label = issue_label(now)
    issue = build_issue(config, all_repos, by_column, history, now, previous_issue(label))

    texts = [e["description"] for c in issue["columns"] for k in LISTS for e in c[k]]
    cache = TranslationCache(TRANSLATIONS)
    if args.skip_translate:
        report = None
    else:
        report = translate_all(texts, cache, config.translation_model)
        cache.save()
    for c in issue["columns"]:
        for k in LISTS:
            for e in c[k]:
                e["description_zh"] = cache.data.get(e["description"])

    ISSUES.mkdir(parents=True, exist_ok=True)
    (ISSUES / f"{label}.json").write_text(json.dumps(issue, ensure_ascii=False, indent=1) + "\n")

    summary(f"## Tracker {label} ({issue['status']})")
    summary(f"- Candidates: {len(all_repos)} repos")
    for c in issue["columns"]:
        summary(f"- {c['name_en']}: {len(c['hot'])} hot, {len(c['rising'])} rising, "
                f"{len(c['all_time'])} all-time")
    if report:
        summary(f"- Translations: {report.translated} new, {report.cached} cached")
        for err in report.transient_errors:
            summary(f"- ⚠️ Translation fell back to English: {err}")
        if report.config_error:
            msg = (f"Translation is misconfigured ({report.config_error}). Descriptions were "
                   f"published in English. Check ANTHROPIC_API_KEY, account credit, and that "
                   f"model {config.translation_model!r} in config.toml is still available.")
            summary(f"- ❌ {msg}")
            TRANSLATION_FLAG.write_text(msg + "\n")


def cmd_build(args: argparse.Namespace) -> None:
    config = load_config()
    cache = TranslationCache(TRANSLATIONS)
    written = build_site(config, ISSUES, cache.data, Path(args.out))
    log.info("wrote %d pages to %s", len(written), args.out)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="tracker")
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("update", help="collect stars, snapshot, rank, translate")
    up.add_argument("--skip-translate", action="store_true")
    up.set_defaults(func=cmd_update)
    b = sub.add_parser("build", help="render the static site")
    b.add_argument("--out", default=str(SITE))
    b.set_defaults(func=cmd_build)
    args = parser.parse_args(argv)
    args.func(args)
