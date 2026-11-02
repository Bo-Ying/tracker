from datetime import datetime, timedelta, timezone

import pytest

from tracker.snapshots import History, Snapshot, SnapshotStore

T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)
OLD = T0 - timedelta(days=365)


def day(n: float) -> datetime:
    return T0 + timedelta(days=n)


def test_exact_snapshot_value():
    h = History([Snapshot(T0, {1: 100})])
    assert h.stars_at(1, OLD, T0) == 100


def test_interpolates_between_snapshots():
    h = History([Snapshot(day(0), {1: 100}), Snapshot(day(7), {1: 800})])
    assert h.stars_at(1, OLD, day(2)) == pytest.approx(300)


def test_thirty_days_back_lands_between_weekly_snapshots():
    snaps = [Snapshot(day(7 * i), {1: 1000 + 700 * i}) for i in range(6)]  # days 0..35
    h = History(snaps)
    # now = day 35, 30 days back = day 5 -> between day 0 (1000) and day 7 (1700)
    assert h.stars_at(1, OLD, day(5)) == pytest.approx(1500)


def test_repo_created_after_target_counts_zero():
    h = History([Snapshot(day(0), {}), Snapshot(day(7), {1: 900})])
    assert h.stars_at(1, day(3), day(1)) == 0


def test_repo_created_between_snapshots_interpolates_from_zero():
    h = History([Snapshot(day(0), {}), Snapshot(day(7), {1: 700})])
    assert h.stars_at(1, day(3), day(5)) == pytest.approx(500)


def test_untracked_older_repo_is_unknown():
    h = History([Snapshot(day(0), {}), Snapshot(day(7), {1: 700})])
    assert h.stars_at(1, OLD, day(5)) is None


def test_before_history_is_unknown():
    h = History([Snapshot(day(0), {1: 100})])
    assert not h.covers(day(-2))
    assert h.stars_at(1, OLD, day(-2)) is None


def test_slightly_before_earliest_clamps():
    h = History([Snapshot(day(0), {1: 100}), Snapshot(day(7), {1: 200})])
    assert h.stars_at(1, OLD, day(-0.01)) == 100


def test_store_roundtrip(tmp_path):
    store = SnapshotStore(tmp_path)
    store.save(Snapshot(day(7), {2: 5}))
    store.save(Snapshot(day(0), {1: 3}))
    snaps = store.load_all()
    assert [s.taken_at for s in snaps] == [day(0), day(7)]
    assert snaps[0].stars == {1: 3}
