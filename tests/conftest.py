import pytest
from pathlib import Path

from todocli.database import Database


@pytest.fixture
def tmp_db(tmp_path: Path) -> Database:
    """Provide a Database instance using a temporary directory."""
    return Database(path=tmp_path / "tasks.json")


@pytest.fixture
def populated_db(tmp_db: Database) -> Database:
    """Provide a Database with 3 pre-loaded tasks (one per context)."""
    tmp_db.add_task("Call venue", context="biz")
    tmp_db.add_task("Buy groceries", context="me")
    tmp_db.add_task("Morning run", context="well")
    return tmp_db
