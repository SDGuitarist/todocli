from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

SCHEMA_VERSION = 1


class Context(str, Enum):
    ME = "me"
    BIZ = "biz"
    WELL = "well"


CONTEXT_TAGS: dict[str, Context] = {
    "@me": Context.ME,
    "@biz": Context.BIZ,
    "@well": Context.WELL,
}


@dataclass
class Task:
    id: str
    text: str
    context: Optional[str] = None
    done: bool = False
    deleted: bool = False
    created_at: str = ""
    done_at: Optional[str] = None
    deleted_at: Optional[str] = None
    due: Optional[str] = None

    @staticmethod
    def create(text: str, context: Optional[str] = None) -> Task:
        now = datetime.now(timezone.utc).isoformat()
        return Task(
            id=uuid.uuid4().hex[:8],
            text=text,
            context=context,
            created_at=now,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> Task:
        known = {f.name for f in __import__('dataclasses').fields(Task)}
        return Task(**{k: v for k, v in data.items() if k in known})


def parse_task_input(raw: str) -> tuple[str, Optional[str]]:
    """Parse raw input like 'Call venue @biz' into (text, context).

    Extracts the first recognized context tag (@me, @biz, @well).
    Tag is removed from the text. Case-insensitive.
    """
    context: Optional[str] = None
    words = raw.split()
    remaining = []
    for word in words:
        lower = word.lower()
        if lower in CONTEXT_TAGS and context is None:
            context = CONTEXT_TAGS[lower].value
        else:
            remaining.append(word)
    text = " ".join(remaining).strip()
    return text, context
