from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from modules.product_drafts import batches, buffer, model
from modules.product_drafts.schema import BatchControl, IngestResult
from shared.db.session import active_session
from shared.jobs.contracts import Job
from tests.modules.product_drafts.helpers import BASE, incoming
from tests.modules.product_drafts.test_services import state as state

pytestmark = pytest.mark.asyncio


@pytest.fixture
def queue(state, monkeypatch):
    assert isinstance(model.stream_for, AsyncMock)
    stream = model.stream_for.return_value
    stream.buffer_until = None
    state[model.BufferedEventTable] = {}
    original_add = active_session().add

    def add(row):
        if isinstance(row, model.BufferedEventTable):
            row.status = row.status or "pending"
        original_add(row)

    async def attach(form, message):
        message.draft_id = uuid4()
        return IngestResult(message_id=str(message.id), draft_id=str(message.draft_id))

    monkeypatch.setattr(active_session(), "add", add)
    monkeypatch.setattr(model, "pending_events", AsyncMock(side_effect=lambda _source:
        sorted((row for row in state[model.BufferedEventTable].values() if row.status == "pending"),
               key=lambda row: row.occurred_at)))
    monkeypatch.setattr(model, "issue_at", AsyncMock(return_value=False))
    monkeypatch.setattr(batches, "attach_buffered_message", AsyncMock(side_effect=attach))
    monkeypatch.setattr(batches, "control_collection", AsyncMock(
        return_value=BatchControl(result="started")))
    monkeypatch.setattr(buffer, "enqueue_job", AsyncMock())
    now = [BASE]
    monkeypatch.setattr(buffer, "utc_now", lambda: now[0])
    return stream, now


async def run():
    await buffer.process_buffer(Job(id=uuid4(), task_name="product_drafts.buffer",
                                   payload={"source_key": "group-a"}, attempts=1))


async def test_buffer_failure_preserves_waiting_state_and_unprocessed_message(queue, state,
                                                                             monkeypatch):
    stream, now = queue
    await buffer.queue_control("group-a", "start", BASE)
    result = await buffer.queue_message(incoming(second=1))
    deadline = stream.buffer_until
    now[0] += timedelta(minutes=3)
    attach = batches.attach_buffered_message
    monkeypatch.setattr(batches, "attach_buffered_message",
                        AsyncMock(side_effect=ConnectionError("temporary failure")))
    with pytest.raises(ConnectionError):
        await run()
    assert stream.buffer_until == deadline
    assert any(str(row.message_id) == result.message_id
               for row in state[model.BufferedEventTable].values())
    monkeypatch.setattr(batches, "attach_buffered_message", attach)
    await run()
    assert stream.buffer_until is None
    assert not state[model.BufferedEventTable]


async def test_buffer_completed_job_replay_does_not_assign_messages_twice(queue, state):
    stream, now = queue
    image = await buffer.queue_message(incoming(second=1))
    await buffer.queue_message(incoming("text", second=2, text="原始文字"))
    now[0] += timedelta(minutes=3)
    await run()
    assert isinstance(batches.attach_buffered_message, AsyncMock)
    assert stream.buffer_until is None
    assert batches.attach_buffered_message.await_count == 2
    assert image.message_id in state[model.MessageTable]
    await run()
    assert batches.attach_buffered_message.await_count == 2


async def test_buffer_redelivery_does_not_reset_wait_or_create_another_job(queue):
    stream, now = queue
    message = incoming(second=1)
    await buffer.queue_message(message)
    deadline = stream.buffer_until
    now[0] += timedelta(seconds=170)
    assert (await buffer.queue_message(message)).duplicate
    assert stream.buffer_until == deadline
    assert isinstance(buffer.enqueue_job, AsyncMock)
    assert isinstance(batches.attach_buffered_message, AsyncMock)
    assert buffer.enqueue_job.await_count == 1
    await run()
    batches.attach_buffered_message.assert_not_awaited()
    assert buffer.enqueue_job.call_args.kwargs["available_at"] == deadline
