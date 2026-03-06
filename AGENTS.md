# Codex Repo Instructions

## Repo Snapshot
- Project: Python CLI todo app for ADHD-friendly task capture and review.
- Read first: `HANDOFF.md`, `AGENTS.md`, `README.md`, `docs/plans/`, `docs/reviews/`, then `pyproject.toml`.
- Main code: `src/todocli/`
- Tests: `tests/`
- Docs: `docs/`
- Config: `pyproject.toml`

## Commands
- Install for development: `pip install -e ".[dev]"` — installs the app plus test tools.
- Run the CLI: `t` — shows the default todo view after the package is installed.
- Run tests: `pytest` — runs the Python test suite in `tests/`.
- Optional web work: `pip install -e ".[dev,web]"` — adds Flask if you are working on the web extra.

## Branch And PR Notes
- Base branch appears to be `main`.
- If PR commands are needed, use `gh pr create --base main`.

## How Codex Should Work Here
- Use Codex for second-opinion plans, risk reviews, plain-English explanation, and Claude Code handoff prompts.
- Keep work scoped to the smallest safe change because this is a simple CLI app.
- When asked to plan, include the exact command behavior, storage impact, tests, rollback, and handoff prompt.
- When asked to review, focus on task loss risk, CLI regressions, soft-delete behavior, missing tests, and user friction.

## Repo Guardrails
- Data lives in `~/.todocli/tasks.json`, so storage and migration changes are high risk.
- Keep the app simple and avoid turning it into a complex productivity system unless I ask.
