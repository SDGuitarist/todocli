from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from todocli.models import SCHEMA_VERSION, Task


def _default_data_path() -> Path:
    return Path.home() / ".todocli" / "tasks.json"


class Database:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or _default_data_path()

    def _ensure_dir(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[Task]:
        """Load all tasks from JSON file. Returns empty list if file missing."""
        if not self.path.exists():
            return []
        raw = self.path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return [Task.from_dict(t) for t in data.get("tasks", [])]

    def save(self, tasks: list[Task]) -> None:
        """Atomic write: temp file -> os.replace -> chmod 600."""
        self._ensure_dir()
        payload = {
            "version": SCHEMA_VERSION,
            "tasks": [t.to_dict() for t in tasks],
        }
        raw = json.dumps(payload, indent=2, ensure_ascii=False)

        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.path.parent),
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(raw)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(self.path))
            os.chmod(str(self.path), 0o600)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def add_task(self, text: str, context: Optional[str] = None) -> Task:
        tasks = self.load()
        task = Task.create(text=text, context=context)
        tasks.append(task)
        self.save(tasks)
        return task

    def get_active_tasks(self, context: Optional[str] = None) -> list[Task]:
        """Return tasks that are not done and not deleted, optionally filtered."""
        tasks = self.load()
        active = [t for t in tasks if not t.done and not t.deleted]
        if context is not None:
            active = [t for t in active if t.context == context]
        return active

    def count_done_today(self) -> int:
        """Count tasks completed today (for celebration counter).

        "Today" is the user's local calendar day: stored timestamps are
        timezone-aware UTC and are converted to local time before comparing.
        """
        tasks = self.load()
        today = datetime.now().astimezone().date()
        count = 0
        for t in tasks:
            if t.done and t.done_at:
                done = datetime.fromisoformat(t.done_at)
                if done.tzinfo is None:
                    # Legacy/offset-less value: treat as UTC, as before.
                    done = done.replace(tzinfo=timezone.utc)
                if done.astimezone().date() == today:
                    count += 1
        return count

    def mark_done(self, task_id: str) -> Optional[Task]:
        """Mark a task as done. Returns the task or None if not found."""
        tasks = self.load()
        target = None
        for t in tasks:
            if t.id == task_id and not t.deleted and not t.done:
                t.done = True
                t.done_at = datetime.now(timezone.utc).isoformat()
                target = t
                break
        if target:
            self.save(tasks)
        return target

    def soft_delete(self, task_id: str) -> Optional[Task]:
        """Soft-delete a task. Returns the task or None if not found."""
        tasks = self.load()
        target = None
        for t in tasks:
            if t.id == task_id and not t.deleted:
                t.deleted = True
                t.deleted_at = datetime.now(timezone.utc).isoformat()
                target = t
                break
        if target:
            self.save(tasks)
        return target
