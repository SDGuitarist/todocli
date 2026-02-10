# todocli

Dead-simple CLI todo app for ADHD brains. One command to capture, one glance to review.

## Install

```sh
pip install .
```

For development:

```sh
pip install -e ".[dev]"
```

## Quick Start

```sh
t add Call venue about Saturday sound check @biz
t add Take a walk @well
t add Buy birthday gift @me
t
```

## Commands

Add a task:

```sh
t add Reply to booking email @biz
```

List active tasks:

```sh
t
t list
t list -c biz
t list --all
```

Mark done:

```sh
t done a1b2c3d4
```

Delete:

```sh
t delete a1b2c3d4
```

## Context Tags

Add `@me`, `@biz`, or `@well` anywhere in the task text.

- `@me` -- personal tasks (cyan)
- `@biz` -- business tasks (yellow)
- `@well` -- wellness reminders (green)

Tags are optional. Tasks without a tag work fine.

## Design Philosophy

Built for ADHD brains:

- Zero friction to capture a thought
- Today's view is the default -- no digging
- Completions are celebrated, not silent
- No guilt messages, ever
- Flat list, no nesting, no complexity

## Data

Tasks are stored in `~/.todocli/tasks.json` (permissions `600`).

Deletes are soft -- your data is never truly lost.

## License

MIT
