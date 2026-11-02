import re

from tracker.github import collect, search_topic


class FakeSearch:
    """Serves repos for `topic:X stars:LO..HI` queries, sorted by stars desc."""

    def __init__(self, repos_by_topic):
        self.repos_by_topic = repos_by_topic
        self.calls = []

    def search(self, query, page):
        self.calls.append((query, page))
        topic = re.search(r"topic:(\S+)", query).group(1)
        lo, hi = map(int, re.search(r"stars:(\d+)\.\.(\d+)", query).groups())
        hits = sorted((r for r in self.repos_by_topic.get(topic, [])
                       if lo <= r["stargazers_count"] <= hi),
                      key=lambda r: -r["stargazers_count"])
        return len(hits), hits[(page - 1) * 100: page * 100]


def item(id, stars):
    return {"id": id, "full_name": f"o/r{id}", "name": f"r{id}", "html_url": "u",
            "description": None, "language": None, "stargazers_count": stars,
            "topics": ["t"], "created_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-01T00:00:00Z"}


def test_small_topic_single_query_paginates():
    fake = FakeSearch({"t": [item(i, 100 + i) for i in range(250)]})
    repos = search_topic(fake, "t", 100)
    assert len(repos) == 250
    assert [p for _, p in fake.calls] == [1, 2, 3]


def test_large_topic_splits_star_ranges_past_cap():
    fake = FakeSearch({"t": [item(i, 100 + i % 3000) for i in range(2500)]})
    repos = search_topic(fake, "t", 100)
    assert len(repos) == 2500


def test_collect_unions_topics_and_shares_repos_across_columns():
    fake = FakeSearch({"a": [item(1, 200), item(2, 300)], "b": [item(2, 300)], "q": [item(2, 300)]})
    all_repos, by_column = collect(fake, {"agents": ("a", "b"), "quant": ("q",)}, 100)
    assert set(all_repos) == {1, 2}
    assert by_column == {"agents": {1, 2}, "quant": {2}}
