from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from todocli.cli import app
from todocli.database import Database

runner = CliRunner()


def _invoke_with_tmp_db(tmp_path: Path, args: list[str]):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        return runner.invoke(app, args)


def test_add_task(tmp_path: Path):
    result = _invoke_with_tmp_db(tmp_path, ["add", "Test", "task"])
    assert result.exit_code == 0
    assert "Test task" in result.output


def test_list_shows_added_task(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        runner.invoke(app, ["add", "Buy", "milk"])
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Buy milk" in result.output


def test_done_marks_task(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        add_result = runner.invoke(app, ["add", "Finish", "report"])
        # Extract task ID from output like "+ Finish report (a1b2c3d4)"
        task_id = add_result.output.strip().split("(")[-1].rstrip(")")
        result = runner.invoke(app, ["done", task_id])
    assert result.exit_code == 0
    assert "done!" in result.output


def test_delete_removes_from_list(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        add_result = runner.invoke(app, ["add", "Temp", "task"])
        task_id = add_result.output.strip().split("(")[-1].rstrip(")")
        runner.invoke(app, ["delete", task_id])
        result = runner.invoke(app, ["list"])
    assert "Temp task" not in result.output


def test_bare_invocation_shows_tasks(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        runner.invoke(app, ["add", "Show", "me"])
        result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Show me" in result.output


def test_empty_list_message(tmp_path: Path):
    result = _invoke_with_tmp_db(tmp_path, ["list"])
    assert "Enjoy the calm" in result.output


def test_done_nonexistent_fails(tmp_path: Path):
    result = _invoke_with_tmp_db(tmp_path, ["done", "fakeid"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_delete_nonexistent_fails(tmp_path: Path):
    result = _invoke_with_tmp_db(tmp_path, ["delete", "fakeid"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_add_with_context(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        result = runner.invoke(app, ["add", "Call", "venue", "@biz"])
    assert result.exit_code == 0
    assert "Call venue" in result.output
    assert "@biz" in result.output


def test_context_parsed_from_middle(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        result = runner.invoke(app, ["add", "@me", "Buy", "groceries"])
    assert result.exit_code == 0
    assert "Buy groceries" in result.output
    assert "@me" in result.output


def test_done_shows_celebration(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        add_result = runner.invoke(app, ["add", "Test", "task"])
        task_id = add_result.output.strip().split("(")[-1].rstrip(")")
        result = runner.invoke(app, ["done", task_id])
    assert "done!" in result.output
    assert "Nice start" in result.output


def test_list_with_context_filter(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        runner.invoke(app, ["add", "Call", "venue", "@biz"])
        runner.invoke(app, ["add", "Buy", "milk", "@me"])
        result = runner.invoke(app, ["list", "-c", "biz"])
    assert "Call venue" in result.output
    assert "Buy milk" not in result.output


def test_list_all_shows_done(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        add_result = runner.invoke(app, ["add", "Finish", "report"])
        task_id = add_result.output.strip().split("(")[-1].rstrip(")")
        runner.invoke(app, ["done", task_id])
        result = runner.invoke(app, ["list", "--all"])
    assert "Finish report" in result.output


def test_help_text(tmp_path: Path):
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ADHD" in result.output


def test_add_help_text(tmp_path: Path):
    result = runner.invoke(app, ["add", "--help"])
    assert result.exit_code == 0
    assert "Add" in result.output


def test_add_unicode_task(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        result = runner.invoke(app, ["add", "Get", "coffee", "\u2615"])
    assert result.exit_code == 0
    assert "coffee" in result.output


def test_multiple_tasks_listed_in_order(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        runner.invoke(app, ["add", "First"])
        runner.invoke(app, ["add", "Second"])
        runner.invoke(app, ["add", "Third"])
        result = runner.invoke(app, ["list"])
    first_pos = result.output.find("First")
    second_pos = result.output.find("Second")
    third_pos = result.output.find("Third")
    assert first_pos < second_pos < third_pos


def test_invalid_context_filter_fails(tmp_path: Path):
    result = _invoke_with_tmp_db(tmp_path, ["list", "-c", "banana"])
    assert result.exit_code == 1
    assert "Unknown context" in result.output


def test_add_only_context_tag_fails(tmp_path: Path):
    result = _invoke_with_tmp_db(tmp_path, ["add", "@biz"])
    assert result.exit_code == 1
    assert "empty" in result.output


def test_rich_markup_in_task_text_escaped(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        result = runner.invoke(app, ["add", "[red]ALERT[/red]"])
    assert result.exit_code == 0
    # The literal brackets should appear, not be interpreted as markup
    assert "ALERT" in result.output


def test_done_already_done_fails(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        add_result = runner.invoke(app, ["add", "Once", "only"])
        task_id = add_result.output.strip().split("(")[-1].rstrip(")")
        runner.invoke(app, ["done", task_id])
        result = runner.invoke(app, ["done", task_id])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_delete_already_deleted_fails(tmp_path: Path):
    db = Database(path=tmp_path / "tasks.json")
    with patch("todocli.cli._get_db", return_value=db):
        add_result = runner.invoke(app, ["add", "Temp"])
        task_id = add_result.output.strip().split("(")[-1].rstrip(")")
        runner.invoke(app, ["delete", task_id])
        result = runner.invoke(app, ["delete", task_id])
    assert result.exit_code == 1
    assert "not found" in result.output
