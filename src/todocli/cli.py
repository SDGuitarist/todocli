from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from rich.markup import escape

from todocli.database import Database
from todocli.models import Context, parse_task_input

app = typer.Typer(
    name="t",
    help="Dead-simple todo list for ADHD brains.",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False,
)
console = Console()

CONTEXT_STYLES: dict[str, str] = {
    "me": "cyan",
    "biz": "yellow",
    "well": "green",
}

CONTEXT_LABELS: dict[str, str] = {
    "me": "@me",
    "biz": "@biz",
    "well": "@well",
}


def _get_db() -> Database:
    """Get database instance. Separate function for test injection."""
    return Database()


def _format_context(ctx: Optional[str]) -> str:
    """Return Rich-styled context tag or empty string."""
    if ctx is None:
        return ""
    style = CONTEXT_STYLES.get(ctx, "white")
    label = CONTEXT_LABELS.get(ctx, f"@{ctx}")
    return f" [{style}]{label}[/{style}]"


def _relative_time(iso_str: str) -> str:
    """Convert ISO timestamp to relative display like '3h ago'."""
    try:
        created = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc)
        diff = now - created
        seconds = int(diff.total_seconds())
        if seconds < 0:
            return "just now"
        elif seconds < 60:
            return "just now"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        else:
            return f"{seconds // 86400}d ago"
    except (ValueError, TypeError):
        return ""


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    """Show active tasks when no command is given."""
    if ctx.invoked_subcommand is None:
        _list_tasks()


@app.command()
def add(
    text: list[str] = typer.Argument(..., help="Task text (include @me/@biz/@well for context)"),
):
    """Add a new task. Example: t add Call venue about sound check @biz"""
    raw = " ".join(text)
    cleaned_text, context = parse_task_input(raw)
    if not cleaned_text:
        console.print("[red]Task text cannot be empty.[/red]")
        raise typer.Exit(code=1)
    db = _get_db()
    task = db.add_task(text=cleaned_text, context=context)
    ctx_display = _format_context(task.context)
    console.print(f"[green]+[/green] {escape(task.text)}{ctx_display} [dim]({task.id})[/dim]")


VALID_CONTEXTS = {c.value for c in Context}


@app.command("list")
def list_cmd(
    context: Optional[str] = typer.Option(
        None, "--context", "-c",
        help="Filter by context: me, biz, well",
    ),
    all_tasks: bool = typer.Option(
        False, "--all", "-a",
        help="Show all tasks including completed",
    ),
):
    """List tasks. Alias: just run `t` with no arguments."""
    if context and context not in VALID_CONTEXTS:
        console.print(f"[red]Unknown context '{escape(context)}'. Use: me, biz, well[/red]")
        raise typer.Exit(code=1)
    _list_tasks(context=context, show_all=all_tasks)


@app.command()
def done(
    task_id: str = typer.Argument(..., help="Task ID to mark as done"),
):
    """Mark a task as done."""
    db = _get_db()
    task = db.mark_done(task_id)
    if task is None:
        console.print(f"[red]Task '{task_id}' not found.[/red]")
        raise typer.Exit(code=1)
    count = db.count_done_today()
    console.print(f"[green]\u2714[/green] {escape(task.text)} [dim]done![/dim]")
    if count == 1:
        console.print("  [dim]First one today. Nice start![/dim]")
    elif count < 5:
        console.print(f"  [dim]{count} done today. Keep rolling![/dim]")
    else:
        console.print(f"  [dim]{count} done today. On fire![/dim]")


@app.command()
def delete(
    task_id: str = typer.Argument(..., help="Task ID to delete"),
):
    """Soft-delete a task (can be recovered later)."""
    db = _get_db()
    task = db.soft_delete(task_id)
    if task is None:
        console.print(f"[red]Task '{task_id}' not found.[/red]")
        raise typer.Exit(code=1)
    console.print(f"[dim]- {escape(task.text)} removed[/dim]")


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    port: int = typer.Option(5000, "--port", "-p", help="Port number"),
    debug: bool = typer.Option(False, "--debug", help="Enable Flask debug mode"),
):
    """Start the web UI (requires: pip install todocli[web])."""
    try:
        from todocli.web import run_server
    except ImportError:
        console.print(
            "[red]Flask is not installed.[/red]\n"
            "Install with: [bold]pip install todocli\\[web][/bold]"
        )
        raise typer.Exit(code=1)
    console.print(f"[green]Starting web UI at http://{host}:{port}[/green]")
    run_server(host=host, port=port, debug=debug)


def _list_tasks(context: Optional[str] = None, show_all: bool = False) -> None:
    """Render the task list as a Rich table."""
    db = _get_db()

    if show_all:
        tasks = db.load()
        tasks = [t for t in tasks if not t.deleted]
        if context:
            tasks = [t for t in tasks if t.context == context]
    else:
        tasks = db.get_active_tasks(context=context)

    if not tasks:
        console.print("[dim]No tasks. Enjoy the calm.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Task", min_width=30)
    table.add_column("", width=8)
    table.add_column("Added", style="dim", width=10)

    for t in tasks:
        escaped_text = escape(t.text)
        if t.done:
            prefix = "[green]\u2714[/green] "
            task_cell = f"{prefix}[strike dim]{escaped_text}[/strike dim]"
        else:
            task_cell = f"  {escaped_text}"

        if t.context and t.context in CONTEXT_STYLES:
            ctx_cell = f"[{CONTEXT_STYLES[t.context]}]{CONTEXT_LABELS[t.context]}[/{CONTEXT_STYLES[t.context]}]"
        else:
            ctx_cell = ""

        table.add_row(
            t.id,
            task_cell,
            ctx_cell,
            _relative_time(t.created_at),
        )

    console.print(table)

    done_count = db.count_done_today()
    if done_count > 0:
        console.print(f"\n[dim]\u2714 {done_count} done today[/dim]")
