"""GitHub search: collect every repo carrying a column's topics."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

log = logging.getLogger(__name__)

SEARCH_CAP = 1000  # GitHub search never returns more than 1,000 results per query
PER_PAGE = 100
MAX_STARS = 10_000_000


@dataclass(frozen=True)
class Repo:
    id: int
    full_name: str
    name: str
    url: str
    description: str
    language: str | None
    stars: int
    topics: tuple[str, ...]
    created_at: str  # ISO 8601, UTC
    pushed_at: str

    @classmethod
    def from_api(cls, item: dict) -> "Repo":
        return cls(
            id=item["id"],
            full_name=item["full_name"],
            name=item["name"],
            url=item["html_url"],
            description=(item.get("description") or "").strip(),
            language=item.get("language"),
            stars=item["stargazers_count"],
            topics=tuple(item.get("topics") or ()),
            created_at=item["created_at"],
            pushed_at=item["pushed_at"],
        )


class SearchClient(Protocol):
    def search(self, query: str, page: int) -> tuple[int, list[dict]]:
        """Return (total_count, items) for one page of repository search."""


class GitHubSearch:
    """Thin REST client for /search/repositories with pacing and retries."""

    # Search allows 30 requests/minute for authenticated callers.
    MIN_INTERVAL = 2.1

    def __init__(self, token: str, max_retries: int = 6):
        self._http = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        self._max_retries = max_retries
        self._last = 0.0

    def search(self, query: str, page: int) -> tuple[int, list[dict]]:
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": PER_PAGE, "page": page}
        for attempt in range(self._max_retries + 1):
            wait = self.MIN_INTERVAL - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                resp = self._http.get("/search/repositories", params=params)
            except httpx.TransportError as e:
                delay = 2**attempt
                log.warning("network error (%s), retrying in %ss", e, delay)
                time.sleep(delay)
                continue
            if resp.status_code == 200:
                data = resp.json()
                if data.get("incomplete_results"):
                    log.warning("incomplete results for %r page %d", query, page)
                return data["total_count"], data["items"]
            if resp.status_code in (403, 429) or resp.status_code >= 500:
                delay = _retry_delay(resp, attempt)
                log.warning("HTTP %d for %r, retrying in %.0fs", resp.status_code, query, delay)
                time.sleep(delay)
                continue
            resp.raise_for_status()
        raise RuntimeError(f"GitHub search failed after {self._max_retries} retries: {query!r}")


def _retry_delay(resp: httpx.Response, attempt: int) -> float:
    if "retry-after" in resp.headers:
        return float(resp.headers["retry-after"]) + 1
    if resp.headers.get("x-ratelimit-remaining") == "0" and "x-ratelimit-reset" in resp.headers:
        return max(float(resp.headers["x-ratelimit-reset"]) - time.time(), 0) + 2
    return min(2**attempt * 5, 300)


def _query(topic: str, lo: int, hi: int) -> str:
    return f"topic:{topic} stars:{lo}..{hi} fork:false archived:false"


def search_topic(client: SearchClient, topic: str, min_stars: int) -> dict[int, Repo]:
    """All repos with `topic` and >= min_stars.

    Results come sorted by stars, descending. When a query matches more than the
    1,000-result cap, we read the first 1,000 and continue from the lowest star
    count seen, so every request returns useful rows.
    """
    repos: dict[int, Repo] = {}
    hi = MAX_STARS
    while True:
        query = _query(topic, min_stars, hi)
        total, items = client.search(query, 1)
        lowest = hi
        page = 1
        while True:
            for item in items:
                repos[item["id"]] = Repo.from_api(item)
                lowest = min(lowest, item["stargazers_count"])
            if not items or page * PER_PAGE >= min(total, SEARCH_CAP):
                break
            page += 1
            _, items = client.search(query, page)
        if total <= SEARCH_CAP:
            return repos
        if lowest >= hi:
            log.warning("topic %s: over %d repos share %d stars; keeping what we have",
                        topic, SEARCH_CAP, hi)
            return repos
        # Overlap on `lowest` so repos sharing that count aren't skipped; ids dedupe.
        hi = lowest


def collect(client: SearchClient, topics_by_column: dict[str, tuple[str, ...]],
            min_stars: int) -> tuple[dict[int, Repo], dict[str, set[int]]]:
    """Return (all repos by id, repo ids per column)."""
    all_repos: dict[int, Repo] = {}
    by_column: dict[str, set[int]] = {}
    cache: dict[str, dict[int, Repo]] = {}
    for column, topics in topics_by_column.items():
        ids: set[int] = set()
        for topic in topics:
            if topic not in cache:
                cache[topic] = search_topic(client, topic, min_stars)
                log.info("topic %-24s %5d repos", topic, len(cache[topic]))
            all_repos.update(cache[topic])
            ids.update(cache[topic])
        by_column[column] = ids
    return all_repos, by_column
