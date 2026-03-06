# HANDOFF — todocli

**Date:** 2026-03-06
**Branch:** `main`
**Phase:** Workflow bootstrap complete. Next: choose one small Plan or Brainstorm before implementation.

## Current State

Todo-app is a small Python CLI with these main surfaces:
- `src/todocli/cli.py` — command-line behavior
- `src/todocli/database.py` — task storage
- `src/todocli/models.py` — task models
- `src/todocli/web.py` — optional web surface
- `tests/` — automated tests for CLI, database, models, and web behavior

This session added workflow support files (`AGENTS.md`, this `HANDOFF.md`, and lightweight docs in `docs/`) so future Codex and Claude sessions can stay scoped. No application code changed in this session.

## Key Artifacts

| Artifact | Location |
|----------|----------|
| Repo instructions | `AGENTS.md` |
| Project overview | `README.md` |
| Package config | `pyproject.toml` |
| Main code | `src/todocli/` |
| Tests | `tests/` |
| Workflow docs | `docs/plans/`, `docs/reviews/` |

## What Remains

- Decide the next small feature, bug fix, or cleanup before starting work
- Keep changes small when they affect command behavior, storage, or soft-delete logic
- Add written plan or review docs only when the change is large enough to need a handoff

## Three Questions

1. **Hardest decision in this session?** How much workflow structure to add. I kept it light so the repo gets better handoffs without becoming process-heavy.
2. **What did you consider changing but left alone, and why?** All source code and tests. This session was only for workflow setup.
3. **Least confident about going into the next phase?** There is no active branch or current feature target yet, so the next session should choose one small goal before coding starts.

## Next Phase

**Plan or Brainstorm** — pick one small change, write a short plan if needed, then implement.

### Prompt for Next Session

```text
Read HANDOFF.md, AGENTS.md, and README.md. Pick one small todo-app change before coding starts. If the change affects command behavior, storage, soft deletes, or the optional web surface, write a short plan first. Relevant files: src/todocli/cli.py, src/todocli/database.py, src/todocli/models.py, src/todocli/web.py, tests/.
```
