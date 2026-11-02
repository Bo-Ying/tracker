"""Weekly star snapshots and point-in-time star estimates.

GitHub no longer exposes when each star was given, so every gain is the
difference between two of our own snapshots. Snapshots are keyed by numeric
repo id so renames and transfers don't break the history.
"""

from __future__ import annotations

import bisect
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# A requested time this far before the earliest snapshot still uses it,
# so a cron run a few minutes early doesn't lose a whole week.
CLAMP = timedelta(days=1)


def parse_time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_time(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Snapshot:
    taken_at: datetime
    stars: dict[int, int]


class SnapshotStore:
    def __init__(self, directory: Path):
        self.dir = directory

    def load_all(self) -> list[Snapshot]:
        snaps = []
        for path in sorted(self.dir.glob("*.json")):
            raw = json.loads(path.read_text())
            snaps.append(Snapshot(
                taken_at=parse_time(raw["taken_at"]),
                stars={int(k): v for k, v in raw["stars"].items()},
            ))
        return sorted(snaps, key=lambda s: s.taken_at)

    def save(self, snap: Snapshot) -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / f"{snap.taken_at.strftime('%Y-%m-%dT%H%M%SZ')}.json"
        body = {
            "taken_at": format_time(snap.taken_at),
            "stars": {str(k): v for k, v in sorted(snap.stars.items())},
        }
        path.write_text(json.dumps(body, separators=(",", ":")) + "\n")
        return path


class History:
    """Answers "how many stars did repo X have at time t?" from snapshots."""

    def __init__(self, snapshots: list[Snapshot]):
        if not snapshots:
            raise ValueError("History needs at least one snapshot")
        self.snaps = sorted(snapshots, key=lambda s: s.taken_at)
        self._times = [s.taken_at for s in self.snaps]

    @property
    def earliest(self) -> datetime:
        return self._times[0]

    def covers(self, t: datetime) -> bool:
        return t >= self.earliest - CLAMP

    def stars_at(self, repo_id: int, created_at: datetime, t: datetime) -> float | None:
        """Estimated stars at `t`, or None when the history can't tell."""
        if not self.covers(t):
            return None
        if created_at >= t:
            return 0.0
        t = max(t, self.earliest)
        i = bisect.bisect_left(self._times, t)
        if i < len(self._times) and self._times[i] == t:
            return self._value(self.snaps[i], repo_id, created_at)
        if i == len(self._times):
            return None  # t is after the latest snapshot
        before, after = self.snaps[i - 1], self.snaps[i]
        a = self._value(before, repo_id, created_at)
        b = self._value(after, repo_id, created_at)
        if a is None or b is None:
            return None
        frac = (t - before.taken_at) / (after.taken_at - before.taken_at)
        return a + (b - a) * frac

    @staticmethod
    def _value(snap: Snapshot, repo_id: int, created_at: datetime) -> float | None:
        if repo_id in snap.stars:
            return float(snap.stars[repo_id])
        if created_at >= snap.taken_at:
            return 0.0  # didn't exist yet
        return None  # existed but wasn't tracked (below threshold or untagged)
