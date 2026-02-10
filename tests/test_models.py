from todocli.models import Task, parse_task_input


def test_parse_no_context():
    text, ctx = parse_task_input("Buy milk")
    assert text == "Buy milk"
    assert ctx is None


def test_parse_biz_context():
    text, ctx = parse_task_input("Call venue @biz")
    assert text == "Call venue"
    assert ctx == "biz"


def test_parse_context_at_start():
    text, ctx = parse_task_input("@well Meditate")
    assert text == "Meditate"
    assert ctx == "well"


def test_parse_me_context():
    text, ctx = parse_task_input("Buy birthday gift @me")
    assert text == "Buy birthday gift"
    assert ctx == "me"


def test_parse_context_case_insensitive():
    text, ctx = parse_task_input("Task @BIZ")
    assert text == "Task"
    assert ctx == "biz"


def test_parse_multiple_contexts_first_wins():
    text, ctx = parse_task_input("@me task @biz")
    assert text == "task @biz"
    assert ctx == "me"


def test_parse_unknown_context_stays():
    text, ctx = parse_task_input("Email @john")
    assert text == "Email @john"
    assert ctx is None


def test_parse_context_in_middle():
    text, ctx = parse_task_input("Call @biz venue about sound check")
    assert text == "Call venue about sound check"
    assert ctx == "biz"


def test_task_create_generates_id():
    task = Task.create("Test")
    assert len(task.id) == 8
    assert all(c in "0123456789abcdef" for c in task.id)


def test_task_roundtrip():
    original = Task.create("Test task", context="biz")
    restored = Task.from_dict(original.to_dict())
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.context == original.context
    assert restored.done == original.done


def test_task_defaults():
    task = Task.create("Test")
    assert task.done is False
    assert task.deleted is False
    assert task.done_at is None
    assert task.deleted_at is None
    assert task.due is None


def test_from_dict_ignores_unknown_keys():
    data = {
        "id": "abc12345",
        "text": "Future field test",
        "context": None,
        "done": False,
        "deleted": False,
        "created_at": "2026-02-09T00:00:00+00:00",
        "done_at": None,
        "deleted_at": None,
        "due": None,
        "future_field": "should be ignored",
        "another_unknown": 42,
    }
    task = Task.from_dict(data)
    assert task.text == "Future field test"
    assert task.id == "abc12345"
