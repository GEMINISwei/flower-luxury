from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GroupEvent(BaseModel):
    id: str
    kind: Literal["image", "text"]
    occurred_at: datetime
    sequence: int


class GroupingPlan(BaseModel):
    groups: list[list[str]]
    unassigned: list[str]


def propose_groups(events: list[GroupEvent]) -> GroupingPlan:
    kinds: dict[datetime, set[str]] = {}
    for item in events:
        kinds.setdefault(item.occurred_at, set()).add(item.kind)
    groups: list[list[str]] = []
    unassigned: list[str] = []
    current: list[str] | None = None
    has_text = False
    for item in sorted(events, key=lambda row: (row.occurred_at, row.sequence)):
        if len(kinds[item.occurred_at]) > 1:
            unassigned.append(item.id)
            current = None
            continue
        if item.kind == "image":
            if current is None or has_text:
                current, has_text = [], False
                groups.append(current)
            current.append(item.id)
        elif current is None:
            unassigned.append(item.id)
        else:
            current.append(item.id)
            has_text = True
    return GroupingPlan(groups=groups, unassigned=unassigned)
