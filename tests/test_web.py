import json
from pathlib import Path

import pytest

from todocli.database import Database
from todocli.web import create_app


@pytest.fixture
def web_client(tmp_path: Path):
    """Provide a Flask test client backed by a temporary database."""
    db = Database(path=tmp_path / "tasks.json")
    app = create_app(db=db)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, db


def test_index_returns_200(web_client):
    client, db = web_client
    response = client.get("/")
    assert response.status_code == 200
    assert b"todocli" in response.data


def test_index_empty_shows_calm_message(web_client):
    client, db = web_client
    response = client.get("/")
    assert b"Enjoy the calm" in response.data


def test_index_contains_pico_css(web_client):
    client, db = web_client
    response = client.get("/")
    assert b"pico" in response.data


def test_index_contains_htmx(web_client):
    client, db = web_client
    response = client.get("/")
    assert b"htmx.org" in response.data


def test_add_task_via_post(web_client):
    client, db = web_client
    response = client.post("/tasks", data={"text": "Buy groceries @me"})
    assert response.status_code == 200
    assert b"Buy groceries" in response.data
    tasks = db.get_active_tasks()
    assert len(tasks) == 1
    assert tasks[0].text == "Buy groceries"
    assert tasks[0].context == "me"


def test_add_task_shows_toast(web_client):
    client, db = web_client
    response = client.post("/tasks", data={"text": "Test toast"})
    trigger = json.loads(response.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "success"
    assert "Added" in trigger["showToast"]["message"]


def test_add_empty_task_returns_error(web_client):
    client, db = web_client
    response = client.post("/tasks", data={"text": ""})
    trigger = json.loads(response.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "error"
    assert "empty" in trigger["showToast"]["message"]


def test_add_context_only_returns_error(web_client):
    client, db = web_client
    response = client.post("/tasks", data={"text": "@biz"})
    assert db.get_active_tasks() == []
    trigger = json.loads(response.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "error"


def test_mark_done(web_client):
    client, db = web_client
    task = db.add_task("Test task")
    response = client.post(f"/tasks/{task.id}/done")
    assert response.status_code == 200
    assert b"Test task" not in response.data
    trigger = json.loads(response.headers["HX-Trigger"])
    assert "Nice start" in trigger["showToast"]["message"]


def test_mark_done_nonexistent(web_client):
    client, db = web_client
    response = client.post("/tasks/fakeid/done")
    trigger = json.loads(response.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "error"
    assert "not found" in trigger["showToast"]["message"]


def test_delete_task(web_client):
    client, db = web_client
    task = db.add_task("Remove me")
    response = client.delete(f"/tasks/{task.id}/delete")
    assert response.status_code == 200
    assert b"Remove me" not in response.data
    all_tasks = db.load()
    assert all_tasks[0].deleted is True


def test_delete_nonexistent(web_client):
    client, db = web_client
    response = client.delete("/tasks/fakeid/delete")
    trigger = json.loads(response.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "error"


def test_filter_by_context(web_client):
    client, db = web_client
    db.add_task("Call venue", context="biz")
    db.add_task("Buy groceries", context="me")
    response = client.get("/tasks?context=biz")
    assert b"Call venue" in response.data
    assert b"Buy groceries" not in response.data


def test_filter_all_contexts(web_client):
    client, db = web_client
    db.add_task("Call venue", context="biz")
    db.add_task("Buy groceries", context="me")
    response = client.get("/tasks")
    assert b"Call venue" in response.data
    assert b"Buy groceries" in response.data


def test_task_text_is_html_escaped(web_client):
    client, db = web_client
    db.add_task("<script>alert('xss')</script>")
    response = client.get("/")
    assert b"&lt;script&gt;alert(" in response.data
    assert b"<script>alert(" not in response.data


def test_celebration_escalates(web_client):
    client, db = web_client
    t1 = db.add_task("Task 1")
    t2 = db.add_task("Task 2")
    client.post(f"/tasks/{t1.id}/done")
    response = client.post(f"/tasks/{t2.id}/done")
    trigger = json.loads(response.headers["HX-Trigger"])
    assert "Keep rolling" in trigger["showToast"]["message"]


def test_done_today_counter_shown(web_client):
    client, db = web_client
    task = db.add_task("Count me")
    db.mark_done(task.id)
    db.add_task("Still active")
    response = client.get("/")
    assert b"1 done today" in response.data


def test_context_badge_rendered(web_client):
    client, db = web_client
    db.add_task("Gym session", context="well")
    response = client.get("/")
    assert b"@well" in response.data
    assert b"ctx-badge-well" in response.data


def test_add_preserves_context_filter(web_client):
    client, db = web_client
    response = client.post(
        "/tasks?context=biz", data={"text": "New biz task @biz"}
    )
    assert response.status_code == 200
    assert b"New biz task" in response.data


def test_delete_shows_removed_toast(web_client):
    client, db = web_client
    task = db.add_task("Bye bye")
    response = client.delete(f"/tasks/{task.id}/delete")
    trigger = json.loads(response.headers["HX-Trigger"])
    assert trigger["showToast"]["level"] == "info"
    assert "Removed" in trigger["showToast"]["message"]


def test_multiple_tasks_listed(web_client):
    client, db = web_client
    db.add_task("First")
    db.add_task("Second")
    db.add_task("Third")
    response = client.get("/")
    assert b"First" in response.data
    assert b"Second" in response.data
    assert b"Third" in response.data
