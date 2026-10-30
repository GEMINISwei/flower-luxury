from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from modules.product_drafts import batches, model
from modules.product_drafts.schema import IngestResult
from tests.modules.product_drafts.helpers import BASE, incoming

pytestmark = pytest.mark.asyncio
SOURCE = "group-a"


def time(second):
    return BASE + timedelta(seconds=second)


class BatchMemory:
    def __init__(self):
        self.stream = SimpleNamespace(last_control_at=None, last_occurred_at=None)
        self.batches: list[model.BatchTable] = []
        self.windows: list[model.WindowTable] = []
        self.drafts: dict[str, model.DraftTable] = {}
        self.issues: list[model.BatchIssueTable] = []
        self.flush = AsyncMock()
        self.store = AsyncMock()
        self.scalars = AsyncMock(side_effect=lambda _query: self.issues[-5:])
        self.scalar = AsyncMock(side_effect=lambda _query: len(self.issues))

    def add(self, row):
        row.id = row.id or uuid4()
        if isinstance(row, model.BatchTable):
            self.batches.append(row)
        elif isinstance(row, model.WindowTable):
            self.windows.append(row)
        elif isinstance(row, model.BatchIssueTable):
            self.issues.append(row)
        else:
            row.version, row.collecting = 1, True
            self.drafts[str(row.id)] = row

    def batch_at(self, _source, occurred_at):
        return next((row for row in reversed(self.batches)
                     if row.started_at <= occurred_at
                     and (row.ended_at is None or row.ended_at >= occurred_at)), None)


@pytest.fixture
def memory(monkeypatch):
    state = BatchMemory()

    @asynccontextmanager
    async def transaction():
        yield state

    async def store(form, stream, draft):
        return IngestResult(message_id=str(uuid4()), draft_id=str(draft.id))

    monkeypatch.setattr(batches, "transaction", transaction)
    monkeypatch.setattr(batches, "active_session", lambda: state)
    monkeypatch.setattr(model, "stream_for", AsyncMock(return_value=state.stream))
    monkeypatch.setattr(model, "latest_batch", AsyncMock(side_effect=lambda _source:
        state.batches[-1] if state.batches else None))
    monkeypatch.setattr(model, "batch_at", AsyncMock(side_effect=state.batch_at))
    monkeypatch.setattr(model, "batch_windows", AsyncMock(side_effect=lambda id:
        [row for row in state.windows if row.batch_id == id]))
    monkeypatch.setattr(model, "current_draft", AsyncMock(side_effect=lambda _source:
        next((row for row in state.drafts.values() if row.collecting), None)))
    monkeypatch.setattr(model, "get_draft_row", AsyncMock(side_effect=state.drafts.get))
    monkeypatch.setattr(batches, "_remember", AsyncMock(return_value=True))
    state.store.side_effect = store
    monkeypatch.setattr(batches, "_store_message", state.store)
    return state


async def ingest(kind="image", second=1):
    return await batches.ingest_batch_message(incoming(
        kind, second=second, text="商品說明" if kind == "text" else None))


async def test_batch_commands_keep_a_single_batch_and_close_the_last_product(memory):
    assert (await batches.control_collection(SOURCE, "end", time(0))).result == "already_stopped"
    assert (await batches.control_collection(SOURCE, "start", time(1))).result == "started"
    repeated = await batches.control_collection(SOURCE, "start", time(2))
    assert repeated.result == "already_collecting"
    assert len(memory.batches) == 1 and memory.batches[0].started_at == time(1)
    first = await ingest(second=3)
    await ingest("text", 4)
    assert (await batches.control_collection(SOURCE, "end", time(5))).result == "stopped"
    assert (await batches.control_collection(SOURCE, "end", time(6))).result == "already_stopped"
    assert not memory.drafts[first.draft_id].collecting
    state = await batches.get_collection_state(SOURCE)
    assert not state.collecting and state.batch_ended_at == time(5)


async def test_batch_original_time_keeps_late_messages_in_the_original_product(memory):
    await batches.control_collection(SOURCE, "start", time(0))
    first = await ingest(second=1)
    await ingest("text", 2)
    second = await ingest(second=5)
    await ingest("text", 6)
    await batches.control_collection(SOURCE, "end", time(8))
    await batches.control_collection(SOURCE, "start", time(9))
    await ingest(second=10)
    delayed = await ingest("text", 3)
    assert delayed.draft_id == first.draft_id and delayed.draft_id != second.draft_id
    assert memory.drafts[first.draft_id].received_at == time(1)
    assert not memory.drafts[first.draft_id].collecting
    assert (await batches.get_collection_state(SOURCE)).collecting
    assert memory.issues == []


async def test_batch_ignored_text_and_outside_messages_never_reach_storage(memory):
    assert (await ingest()).message_id is None
    await batches.control_collection(SOURCE, "start", time(2))
    assert (await ingest("text", 3)).message_id is None
    first = await ingest(second=5)
    assert (await ingest("text", 4)).message_id is None
    assert (await ingest(second=4)).message_id is None
    assert first.draft_id and len(memory.drafts) == 1
    assert memory.store.await_count == 1
    assert [row.reason for row in memory.issues] == ["ambiguous"]


async def test_batch_late_text_cannot_split_existing_images(memory):
    await batches.control_collection(SOURCE, "start", time(0))
    first = await ingest(second=1)
    await ingest(second=4)
    await ingest("text", 5)
    result = await ingest("text", 2)
    assert result.message_id is None and len(memory.drafts) == 1
    assert memory.windows[0].draft_key == first.draft_id
    assert memory.issues[0].reason == "boundary"
    assert memory.store.await_count == 3


async def test_batch_removed_product_only_leaves_an_issue_without_raw_content(memory):
    await batches.control_collection(SOURCE, "start", time(0))
    await ingest(second=1)
    await ingest("text", 2)
    await batches.control_collection(SOURCE, "end", time(5))
    memory.drafts.clear()
    result = await ingest("text", 3)
    assert result.message_id is None and memory.drafts == {}
    assert memory.issues[0].reason == "removed"
    assert not hasattr(memory.issues[0], "text")
    state = await batches.get_collection_state(SOURCE)
    assert state.issue_count == 1 and "已審核或放棄" in state.issues[0].reason


async def test_batch_ambiguous_commands_do_not_change_collecting_state(memory):
    await batches.control_collection(SOURCE, "start", time(0))
    await ingest(second=4)
    assert (await batches.control_collection(SOURCE, "end", time(2))).result == "unsafe"
    assert (await batches.control_collection(SOURCE, "end", time(4))).result == "unsafe"
    assert (await batches.get_collection_state(SOURCE)).collecting
    assert [row.reason for row in memory.issues] == ["command", "command"]


async def test_manual_batch_end_contains_all_committed_events(memory):
    await batches.control_collection(SOURCE, "start", time(0))
    first = await ingest(second=4)
    state = await batches.finish_collection(SOURCE, time(2))
    assert state.batch_ended_at == time(4) + timedelta(microseconds=1)
    assert not state.collecting and not memory.drafts[first.draft_id].collecting
    assert (await ingest(second=5)).message_id is None


async def test_duplicate_batch_event_does_not_advance_the_timeline(memory, monkeypatch):
    await batches.control_collection(SOURCE, "start", time(0))
    await ingest(second=1)
    monkeypatch.setattr(batches, "_remember", AsyncMock(return_value=False))
    assert (await ingest("text", 2)).duplicate
    assert memory.stream.last_occurred_at == time(1)
    assert memory.store.await_count == 1


@pytest.mark.parametrize("kind,second,expected", [
    ("image", 1, None), ("image", 2, None), ("image", 3, "boundary"),
    ("text", 1, "ambiguous"), ("text", 2, "boundary"), ("text", 3, None),
    ("text", 4, None), ("image", 5, "ambiguous"),
])
async def test_batch_time_ties_do_not_shift_product_boundaries(kind, second, expected):
    window = model.WindowTable(started_at=time(1), last_image_at=time(2),
                               first_text_at=time(3), ended_at=time(5))
    form = incoming(kind, second=second, text="說明" if kind == "text" else None)
    assert batches._unsafe_reason(form, window) == expected
