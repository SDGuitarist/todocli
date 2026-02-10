"""Lightweight web companion for todocli.

Run with: t web
"""
from __future__ import annotations

import json
from typing import Optional

from flask import Flask, make_response, render_template_string, request

from todocli.database import Database
from todocli.models import parse_task_input

_db: Optional[Database] = None


def _get_db() -> Database:
    """Get database instance. Separate function for test injection."""
    global _db
    if _db is None:
        _db = Database()
    return _db


def create_app(db: Optional[Database] = None) -> Flask:
    """Flask app factory. Pass a Database instance for testing."""
    global _db
    if db is not None:
        _db = db

    app = Flask(__name__)
    app.jinja_env.autoescape = True

    @app.route("/")
    def index():
        context_filter = request.args.get("context")
        d = _get_db()
        tasks = d.get_active_tasks(context=context_filter)
        done_today = d.count_done_today()
        task_list_html = render_template_string(
            TASK_LIST_PARTIAL,
            tasks=tasks,
            done_today=done_today,
            active_filter=context_filter,
        )
        return render_template_string(
            PAGE_TEMPLATE,
            task_list_html=task_list_html,
            active_filter=context_filter,
        )

    @app.route("/tasks", methods=["GET"])
    def task_list():
        context_filter = request.args.get("context")
        d = _get_db()
        tasks = d.get_active_tasks(context=context_filter)
        done_today = d.count_done_today()
        return render_template_string(
            TASK_LIST_PARTIAL,
            tasks=tasks,
            done_today=done_today,
            active_filter=context_filter,
        )

    @app.route("/tasks", methods=["POST"])
    def add_task():
        raw = request.form.get("text", "").strip()
        d = _get_db()
        context_filter = request.args.get("context")

        if not raw:
            return _task_list_response(d, context_filter, "Task text cannot be empty.", "error")

        text, context = parse_task_input(raw)
        if not text:
            return _task_list_response(d, context_filter, "Task text cannot be empty.", "error")

        d.add_task(text=text, context=context)
        return _task_list_response(d, context_filter, f"Added: {text}", "success")

    @app.route("/tasks/<task_id>/done", methods=["POST"])
    def mark_done(task_id):
        d = _get_db()
        context_filter = request.args.get("context")
        task = d.mark_done(task_id)

        if task is None:
            return _task_list_response(d, context_filter, "Task not found.", "error")

        done_count = d.count_done_today()
        if done_count == 1:
            celebration = "First one today. Nice start!"
        elif done_count < 5:
            celebration = f"{done_count} done today. Keep rolling!"
        else:
            celebration = f"{done_count} done today. On fire!"

        return _task_list_response(d, context_filter, celebration, "celebration")

    @app.route("/tasks/<task_id>/delete", methods=["DELETE"])
    def delete_task(task_id):
        d = _get_db()
        context_filter = request.args.get("context")
        task = d.soft_delete(task_id)

        if task is None:
            return _task_list_response(d, context_filter, "Task not found.", "error")

        return _task_list_response(d, context_filter, f"Removed: {task.text}", "info")

    def _task_list_response(d, context_filter, message, level):
        tasks = d.get_active_tasks(context=context_filter)
        done_today = d.count_done_today()
        html = render_template_string(
            TASK_LIST_PARTIAL,
            tasks=tasks,
            done_today=done_today,
            active_filter=context_filter,
        )
        resp = make_response(html)
        resp.headers["HX-Trigger"] = json.dumps(
            {"showToast": {"message": message, "level": level}}
        )
        return resp

    return app


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Start the Flask development server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TASK_LIST_PARTIAL = """\
{% if tasks %}
<ul class="task-list">
  {% for task in tasks %}
  <li class="task-item" data-context="{{ task.context or '' }}">
    <button class="done-btn"
            hx-post="/tasks/{{ task.id }}/done{% if active_filter %}?context={{ active_filter }}{% endif %}"
            hx-target="#task-container"
            hx-swap="innerHTML"
            aria-label="Mark done: {{ task.text }}"
            title="Done">&#x2714;</button>
    <span class="task-text">{{ task.text }}</span>
    {% if task.context %}
    <span class="ctx-badge ctx-badge-{{ task.context }}">@{{ task.context }}</span>
    {% endif %}
    <button class="del-btn"
            hx-delete="/tasks/{{ task.id }}/delete{% if active_filter %}?context={{ active_filter }}{% endif %}"
            hx-target="#task-container"
            hx-swap="innerHTML"
            hx-confirm="Remove this task?"
            aria-label="Delete: {{ task.text }}"
            title="Delete">&times;</button>
  </li>
  {% endfor %}
</ul>
{% if done_today > 0 %}
<p class="done-counter">&#x2714; {{ done_today }} done today</p>
{% endif %}
{% else %}
<p class="empty-state">No tasks. Enjoy the calm.</p>
{% endif %}
"""

PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>todocli</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <style>
    :root {
      --ctx-me: #06b6d4;
      --ctx-biz: #eab308;
      --ctx-well: #22c55e;
    }

    body {
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 640px;
      margin: 0 auto;
      padding: 1.5rem 1rem;
    }

    h1 {
      font-size: 1.4rem;
      font-weight: 500;
      text-align: center;
      margin-bottom: 1.5rem;
    }

    /* --- Add form --- */
    .add-form {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
    }
    .add-form input[type="text"] {
      flex: 1;
      min-height: 44px;
      font-size: 1rem;
    }
    .add-form button[type="submit"] {
      min-width: 44px;
      min-height: 44px;
      font-size: 1.2rem;
      cursor: pointer;
    }

    /* --- Filter bar --- */
    .filter-bar {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
    }
    .filter-btn {
      min-height: 36px;
      padding: 0.25rem 0.75rem;
      border-radius: 999px;
      border: 1px solid rgba(128,128,128,0.3);
      background: none;
      cursor: pointer;
      font-size: 0.85rem;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      color: inherit;
    }
    .filter-btn:hover { background: rgba(128,128,128,0.1); }
    .filter-btn.active { font-weight: 700; border-width: 2px; }

    /* --- Task list --- */
    .task-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .task-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.65rem 0.5rem;
      border-left: 4px solid transparent;
      border-radius: 6px;
      margin-bottom: 0.35rem;
    }
    .task-item[data-context="me"]   { border-left-color: var(--ctx-me); }
    .task-item[data-context="biz"]  { border-left-color: var(--ctx-biz); }
    .task-item[data-context="well"] { border-left-color: var(--ctx-well); }

    .task-text { flex: 1; font-size: 1rem; }

    /* --- Context badges --- */
    .ctx-badge {
      font-size: 0.72rem;
      padding: 0.1rem 0.45rem;
      border-radius: 999px;
      font-weight: 600;
      white-space: nowrap;
    }
    .ctx-badge-me   { background: rgba(6,182,212,0.15); color: var(--ctx-me); }
    .ctx-badge-biz  { background: rgba(234,179,8,0.15);  color: var(--ctx-biz); }
    .ctx-badge-well { background: rgba(34,197,94,0.15);  color: var(--ctx-well); }

    /* --- Action buttons --- */
    .done-btn, .del-btn {
      min-width: 36px;
      min-height: 36px;
      border: none;
      background: none;
      cursor: pointer;
      border-radius: 6px;
      font-size: 1rem;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: inherit;
      opacity: 0.4;
      transition: opacity 0.15s, background 0.15s;
    }
    .done-btn:hover { opacity: 1; background: rgba(34,197,94,0.15); }
    .del-btn  { margin-left: auto; }
    .del-btn:hover  { opacity: 1; background: rgba(239,68,68,0.15); }

    /* --- Empty state --- */
    .empty-state {
      text-align: center;
      padding: 3rem 1rem;
      opacity: 0.5;
      font-style: italic;
    }

    /* --- Done counter --- */
    .done-counter {
      text-align: center;
      font-size: 0.85rem;
      opacity: 0.45;
      margin-top: 1rem;
    }

    /* --- Toast --- */
    .toast {
      position: fixed;
      bottom: 1.5rem;
      left: 50%;
      transform: translateX(-50%) translateY(10px);
      padding: 0.65rem 1.25rem;
      border-radius: 8px;
      font-size: 0.9rem;
      z-index: 1000;
      opacity: 0;
      transition: opacity 0.25s ease, transform 0.25s ease;
      pointer-events: none;
    }
    .toast.show {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
    .toast-success     { background: #22c55e; color: #000; }
    .toast-celebration { background: #f59e0b; color: #000; }
    .toast-error       { background: #ef4444; color: #fff; }
    .toast-info        { background: #6b7280; color: #fff; }

    /* --- Keyboard hints --- */
    .kbd-hint {
      text-align: center;
      margin-top: 2rem;
      font-size: 0.7rem;
      opacity: 0.25;
    }
    .kbd-hint kbd {
      display: inline-block;
      padding: 1px 5px;
      font-size: 0.65rem;
      font-family: inherit;
      border: 1px solid rgba(128,128,128,0.3);
      border-radius: 3px;
    }

    /* --- Reduced motion --- */
    @media (prefers-reduced-motion: reduce) {
      .toast { transition: none; }
      .done-btn, .del-btn { transition: none; }
    }
  </style>
</head>
<body>
  <main>
    <h1>todocli</h1>

    <form class="add-form"
          hx-post="/tasks{% if active_filter %}?context={{ active_filter }}{% endif %}"
          hx-target="#task-container"
          hx-swap="innerHTML"
          hx-on::after-request="if(event.detail.successful){this.reset();this.querySelector('input').focus();}">
      <input type="text" name="text"
             placeholder="Add a task... (@me @biz @well)"
             autofocus autocomplete="off" required
             aria-label="New task">
      <button type="submit" aria-label="Add task">+</button>
    </form>

    <nav class="filter-bar" role="tablist" aria-label="Filter tasks">
      <a class="filter-btn {% if not active_filter %}active{% endif %}"
         href="/"
         hx-get="/tasks"
         hx-target="#task-container"
         hx-push-url="/">All</a>
      <a class="filter-btn {% if active_filter == 'me' %}active{% endif %}"
         href="/?context=me"
         hx-get="/tasks?context=me"
         hx-target="#task-container"
         hx-push-url="/?context=me">@me</a>
      <a class="filter-btn {% if active_filter == 'biz' %}active{% endif %}"
         href="/?context=biz"
         hx-get="/tasks?context=biz"
         hx-target="#task-container"
         hx-push-url="/?context=biz">@biz</a>
      <a class="filter-btn {% if active_filter == 'well' %}active{% endif %}"
         href="/?context=well"
         hx-get="/tasks?context=well"
         hx-target="#task-container"
         hx-push-url="/?context=well">@well</a>
    </nav>

    <div id="task-container">
      {{ task_list_html | safe }}
    </div>

    <div id="toast" class="toast" role="status" aria-live="polite"></div>

    <div class="kbd-hint">
      <kbd>a</kbd> add &middot;
      <kbd>1</kbd> @me &middot;
      <kbd>2</kbd> @biz &middot;
      <kbd>3</kbd> @well &middot;
      <kbd>0</kbd> all
    </div>
  </main>

  <script>
    document.body.addEventListener("showToast", function(evt) {
      var toast = document.getElementById("toast");
      var data = evt.detail;
      toast.textContent = data.message;
      toast.className = "toast toast-" + (data.level || "info") + " show";
      clearTimeout(toast._timer);
      toast._timer = setTimeout(function() {
        toast.classList.remove("show");
      }, 2500);
    });

    document.addEventListener("keydown", function(e) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
        if (e.key === "Escape") e.target.blur();
        return;
      }
      switch (e.key) {
        case "a":
          e.preventDefault();
          document.querySelector('.add-form input[name="text"]').focus();
          break;
        case "1":
          document.querySelector('a[href="/?context=me"]').click();
          break;
        case "2":
          document.querySelector('a[href="/?context=biz"]').click();
          break;
        case "3":
          document.querySelector('a[href="/?context=well"]').click();
          break;
        case "0":
          document.querySelector('a[href="/"]').click();
          break;
      }
    });
  </script>
</body>
</html>
"""
