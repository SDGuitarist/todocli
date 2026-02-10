---
title: ADHD-Friendly CLI Todo App Design Patterns
date: 2026-02-09
category: architecture-decisions
tags:
  - cli-design
  - data-durability
  - atomic-writes
  - schema-versioning
  - soft-deletes
  - backwards-compatibility
  - adhd-ux
  - typer
  - rich
module: todocli
symptoms: Documenting architectural decisions and design patterns from building a CLI todo app optimized for ADHD brains
severity: low
summary: todocli implements atomic JSON writes, soft deletes, context tag parsing, celebration UX, and comprehensive test isolation to deliver a zero-friction CLI todo experience.
---

# ADHD-Friendly CLI Todo App Design Patterns

## Problem Statement

Build a CLI todo app that works *with* ADHD brains instead of against them. The core tension: most todo apps add friction (categories, priorities, due dates, projects) that creates cognitive overhead. The goal was zero friction to capture a thought, one glance to review, and positive reinforcement on completion.

## Solution: Key Design Patterns

### 1. Atomic File Writes

**Problem**: JSON file corruption on crash or power loss loses all task data.

**Solution**: Write to temp file, fsync, then atomic rename.

```python
fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
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
```

**Why it works**: `os.replace()` is atomic on POSIX. Readers never see a partial write. The temp file cleanup in `except` prevents orphaned files. `chmod 600` restricts access to owner only.

### 2. Soft Deletes

**Problem**: Hard deletes are irreversible. ADHD users may impulsively delete tasks they later need.

**Solution**: `deleted` flag + `deleted_at` timestamp. Data is never physically removed.

```python
def soft_delete(self, task_id: str) -> Optional[Task]:
    tasks = self.load()
    for t in tasks:
        if t.id == task_id and not t.deleted:
            t.deleted = True
            t.deleted_at = datetime.now(timezone.utc).isoformat()
            ...
```

The README explicitly states: *"Deletes are soft -- your data is never truly lost."*

### 3. Context Tag Parsing

**Problem**: Categories add friction. Typing `--category biz` is too many keystrokes.

**Solution**: Inline `@tags` parsed from anywhere in the text. Case-insensitive. First match wins. Unknown `@tags` stay in the text.

```python
def parse_task_input(raw: str) -> tuple[str, Optional[str]]:
    context = None
    words = raw.split()
    remaining = []
    for word in words:
        lower = word.lower()
        if lower in CONTEXT_TAGS and context is None:
            context = CONTEXT_TAGS[lower].value
        else:
            remaining.append(word)
    return " ".join(remaining).strip(), context
```

Usage: `t add Call venue about sound check @biz` -- the `@biz` is extracted, "Call venue about sound check" becomes the text.

### 4. CLI Architecture with Typer

**Problem**: The command should be as short as possible. Bare invocation should show tasks (not help text).

**Solution**: Single-letter command `t` via `pyproject.toml` entry point. `invoke_without_command=True` + callback makes bare `t` show the task list.

```python
app = typer.Typer(
    name="t",
    invoke_without_command=True,
    no_args_is_help=False,
)

@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _list_tasks()
```

**Testability**: A `_get_db()` factory function enables test injection via `mock.patch`, keeping the module-level `app` clean.

### 5. Rich Markup Escaping

**Problem**: User input like `[red]ALERT[/red]` could be interpreted as Rich markup, breaking output formatting.

**Solution**: All user text passes through `rich.markup.escape()` before rendering.

```python
from rich.markup import escape
console.print(f"[green]+[/green] {escape(task.text)}{ctx_display}")
```

Tested explicitly:
```python
def test_rich_markup_in_task_text_escaped(tmp_path):
    result = runner.invoke(app, ["add", "[red]ALERT[/red]"])
    assert result.exit_code == 0
    assert "ALERT" in result.output
```

### 6. Celebration UX (No Guilt)

**Problem**: Most todo apps are silent on completion or add guilt ("You have 47 overdue tasks").

**Solution**: Encouraging messages based on daily completion count. Positive empty state.

```python
if count == 1:
    console.print("  [dim]First one today. Nice start![/dim]")
elif count < 5:
    console.print(f"  [dim]{count} done today. Keep rolling![/dim]")
else:
    console.print(f"  [dim]{count} done today. On fire![/dim]")
```

Empty list: `"No tasks. Enjoy the calm."` -- not "You have no tasks" or "Add some tasks!"

### 7. Schema Versioning & Forward Compatibility

**Problem**: Adding new fields to Task will break old JSON files.

**Solution**: Two mechanisms working together:
- `SCHEMA_VERSION` in the JSON payload for future migration detection
- `from_dict()` ignores unknown keys so old code can read new files

```python
@staticmethod
def from_dict(data: dict) -> Task:
    known = {f.name for f in __import__('dataclasses').fields(Task)}
    return Task(**{k: v for k, v in data.items() if k in known})
```

### 8. Test Strategy: Mirror Module Structure

**Problem**: How to organize tests for a small but non-trivial CLI app.

**Solution**: Three test files mirror three source modules. Shared fixtures in `conftest.py`.

```
src/todocli/models.py    -> tests/test_models.py    (11 tests)
src/todocli/database.py  -> tests/test_database.py  (17 tests)
src/todocli/cli.py       -> tests/test_cli.py       (25 tests)
                            tests/conftest.py        (shared fixtures)
```

CLI tests use `CliRunner` + `mock.patch("todocli.cli._get_db")` for full isolation from the real filesystem.

## Prevention & Best Practices

### Concurrent Access

todocli is a single-user CLI. The atomic write pattern protects against crash corruption but not concurrent writes from multiple processes. This is acceptable for the intended use case. If multi-user support is ever needed, add file locking (`fcntl` on Unix).

### Schema Migration Pattern

When adding new Task fields:
1. Increment `SCHEMA_VERSION` in `models.py`
2. Add a migration function in `database.py`
3. Apply migrations at load time based on version number
4. Test that old-format files load correctly after migration

### Rich Output Checklist

When adding new `console.print()` calls:
- User-provided text: always wrap in `escape()`
- System-generated values (IDs, timestamps): safe to use directly
- Add a test that includes Rich markup characters in user input

### Test Maintenance

When adding a new feature:
- Add tests to the corresponding test file (mirror the module)
- Use `tmp_path` fixture for filesystem isolation
- Use `mock.patch("todocli.cli._get_db")` for CLI test isolation
- Test both success and failure paths

### File Permission Security

Any new persistent storage files must:
- Use `os.chmod(path, 0o600)` after writing
- Have a test verifying permissions
- Use the same atomic write pattern as `database.py`

## Related Documentation

This is the first solution doc for the todocli project.

Cross-references:
- `README.md` > Design Philosophy section for the ADHD-friendly principles
- `README.md` > Data section for storage location and soft-delete guarantee

## Key Takeaway

The app's value comes from what it *doesn't* do. No priorities, no due dates, no projects, no nesting. Every design decision was filtered through: "Does this add friction for an ADHD brain?" If yes, it was cut. The architecture supports this philosophy -- flat JSON, inline tags, single-letter command, celebration on completion, calm on empty.
