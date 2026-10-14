import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from todocli.database import Database


def test_add_and_load(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    task = db.add_task("Buy guitar strings")
    loaded = db.load()
    assert len(loaded) == 1
    assert loaded[0].text == "Buy guitar strings"
    assert loaded[0].id == task.id


def test_mark_done(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    task = db.add_task("Book studio")
    result = db.mark_done(task.id)
    assert result is not None
    assert result.done is True
    assert result.done_at is not None


def test_soft_delete(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    task = db.add_task("Cancel subscription")
    result = db.soft_delete(task.id)
    assert result is not None
    assert result.deleted is True
    assert result.deleted_at is not None


def test_get_active_excludes_done_and_deleted(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    t1 = db.add_task("Active task")
    t2 = db.add_task("Done task")
    t3 = db.add_task("Deleted task")
    db.mark_done(t2.id)
    db.soft_delete(t3.id)
    active = db.get_active_tasks()
    assert len(active) == 1
    assert active[0].id == t1.id


def test_empty_database_returns_empty_list(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    assert db.load() == []


def test_mark_done_nonexistent_returns_none(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    assert db.mark_done("fakeid") is None


def test_soft_delete_nonexistent_returns_none(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    assert db.soft_delete("fakeid") is None


def test_get_active_filtered_by_context(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    db.add_task("Call venue", context="biz")
    db.add_task("Buy groceries", context="me")
    db.add_task("Morning run", context="well")
    biz_tasks = db.get_active_tasks(context="biz")
    assert len(biz_tasks) == 1
    assert biz_tasks[0].text == "Call venue"


def test_count_done_today(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    t1 = db.add_task("Task 1")
    t2 = db.add_task("Task 2")
    db.add_task("Task 3")
    db.mark_done(t1.id)
    db.mark_done(t2.id)
    assert db.count_done_today() == 2


def test_atomic_write_permissions(tmp_path: Path):
    import stat
    db = Database(path=tmp_path / "tasks.json")
    db.add_task("Test permissions")
    mode = oct(db.path.stat().st_mode & 0o777)
    assert mode == "0o600"


def test_schema_version_in_json(tmp_path: Path):
    import json
    db = Database(path=tmp_path / "tasks.json")
    db.add_task("Version check")
    raw = json.loads(db.path.read_text(encoding="utf-8"))
    assert raw["version"] == 1


def test_utf8_encoding(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    db.add_task("Cafe latte \u2615 emoji test")
    loaded = db.load()
    assert loaded[0].text == "Cafe latte \u2615 emoji test"


def test_save_creates_parent_directory(tmp_path: Path):
    db = Database(path=tmp_path / "a" / "b" / "tasks.json")
    db.add_task("Nested dir test")
    assert db.path.exists()
    loaded = db.load()
    assert len(loaded) == 1


def test_soft_delete_preserves_task(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    task = db.add_task("Keep me around")
    db.soft_delete(task.id)
    all_tasks = db.load()
    assert len(all_tasks) == 1
    assert all_tasks[0].deleted is True
    assert all_tasks[0].text == "Keep me around"


def test_mark_done_sets_valid_timestamp(tmp_path: Path):
    from datetime import datetime
    db = Database(path=tmp_path / "tasks.json")
    task = db.add_task("Timestamp check")
    result = db.mark_done(task.id)
    datetime.fromisoformat(result.done_at)  # should not raise


def test_populated_db_fixture(populated_db: Database):
    """Test using the shared populated_db fixture from conftest."""
    active = populated_db.get_active_tasks()
    assert len(active) == 3


def test_mark_done_already_done_returns_none(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    task = db.add_task("Already done")
    db.mark_done(task.id)
    result = db.mark_done(task.id)
    assert result is None


def test_soft_delete_already_deleted_returns_none(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    task = db.add_task("Already deleted")
    db.soft_delete(task.id)
    result = db.soft_delete(task.id)
    assert result is None


def test_redone_does_not_inflate_count(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    task = db.add_task("Count once")
    db.mark_done(task.id)
    db.mark_done(task.id)  # returns None, no double-count
    assert db.count_done_today() == 1


@pytest.fixture
def pacific_local_tz():
    """Make the machine's local timezone US/Pacific for one test, then restore."""
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset() not available on this platform")
    original = os.environ.get("TZ")
    os.environ["TZ"] = "America/Los_Angeles"
    time.tzset()
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()


def _freeze_now(monkeypatch, instant: datetime) -> None:
    """Make todocli.database see `instant` as the current time."""

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant

    monkeypatch.setattr("todocli.database.datetime", FrozenDatetime)


def _add_completed(db: Database, text: str, done_at: str) -> None:
    """Add a task and store an explicit done_at (mark_done uses the wall clock)."""
    task = db.add_task(text)
    tasks = db.load()
    for t in tasks:
        if t.id == task.id:
            t.done = True
            t.done_at = done_at
    db.save(tasks)


def test_count_done_today_uses_local_day_for_evening_completion(
    tmp_path: Path, pacific_local_tz, monkeypatch
):
    # "Now" 2026-10-13T02:00Z is Oct 12, 7 PM in Los Angeles.
    _freeze_now(monkeypatch, datetime(2026, 10, 13, 2, 0, tzinfo=timezone.utc))
    db = Database(path=tmp_path / "tasks.json")
    # Completed Oct 12, 10 AM local: still "today" locally.
    _add_completed(db, "Evening task", "2026-10-12T17:00:00+00:00")
    assert db.count_done_today() == 1


def test_count_done_today_excludes_previous_local_evening(
    tmp_path: Path, pacific_local_tz, monkeypatch
):
    # "Now" 2026-10-13T15:00Z is Oct 13, 8 AM in Los Angeles.
    _freeze_now(monkeypatch, datetime(2026, 10, 13, 15, 0, tzinfo=timezone.utc))
    db = Database(path=tmp_path / "tasks.json")
    # Completed Oct 12, 8 PM local: same UTC date as "now" but not today locally.
    _add_completed(db, "Last night", "2026-10-13T03:00:00+00:00")
    assert db.count_done_today() == 0


def test_count_done_today_handles_dst_fallback(
    tmp_path: Path, pacific_local_tz, monkeypatch
):
    # US Pacific falls back on 2026-11-01, so Nov 1 is a 25-hour local day and
    # the UTC offset differs between its start (PDT, -7) and end (PST, -8).
    # "Now" 2026-11-02T07:30Z is Nov 1, 11:30 PM PST (offset -8).
    _freeze_now(monkeypatch, datetime(2026, 11, 2, 7, 30, tzinfo=timezone.utc))
    db = Database(path=tmp_path / "tasks.json")
    # 07:30Z Nov 1 is 12:30 AM PDT (offset -7): today. Using "now"'s offset
    # (-8) would wrongly place it on Oct 31, and its UTC date is not today's.
    _add_completed(db, "After local midnight", "2026-11-01T07:30:00+00:00")
    # 06:30Z Nov 1 is 11:30 PM PDT on Oct 31: not today.
    _add_completed(db, "Before local midnight", "2026-11-01T06:30:00+00:00")
    assert db.count_done_today() == 1


def test_count_done_today_treats_naive_timestamp_as_utc(
    tmp_path: Path, pacific_local_tz, monkeypatch
):
    # Now is Oct 13, 8 AM local. A naive done_at has no offset; it is read as
    # UTC, i.e. Oct 12, 8 PM local, so it is not today.
    _freeze_now(monkeypatch, datetime(2026, 10, 13, 15, 0, tzinfo=timezone.utc))
    db = Database(path=tmp_path / "tasks.json")
    _add_completed(db, "Legacy timestamp", "2026-10-13T03:00:00")
    assert db.count_done_today() == 0
