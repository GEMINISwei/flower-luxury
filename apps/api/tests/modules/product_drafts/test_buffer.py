from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from modules.product_drafts import buffer, model, photos, service, storage
from shared.db.session import active_session
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from tests.modules.product_drafts.helpers import BASE, image_bytes, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def clock(monkeypatch, tmp_path):
    now = [BASE]
    monkeypatch.setattr(buffer, "utc_now", lambda: now[0])
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path)
    return now


async def process(source="group-a"):
    await buffer.process_buffer(Job(id=uuid4(), task_name="product_drafts.buffer",
                                   payload={"source_key": source}, attempts=1))


async def start():
    await buffer.queue_control("group-a", "start", BASE)


async def test_buffer_waits_three_minutes_and_keeps_photos_before_grouping(db, clock):
    await start()
    result = await buffer.queue_message(incoming(second=1))
    assert result.message_id and not result.draft_id
    await photos.complete_photo(result.message_id, image_bytes(), "original.png")
    clock[0] += timedelta(seconds=179)
    await process()
    assert (await service.get_draft_list(20)).total_count == 0
    clock[0] += timedelta(seconds=1)
    await process()
    draft = (await service.get_draft_list(20)).list_data[0]
    assert draft.collecting
    assert (await service.get_draft(draft.id)).photos[0].status == "ready"


async def test_buffer_sorts_reversed_images_text_and_controls_by_original_time(db, clock):
    await buffer.queue_control("group-a", "end", BASE + timedelta(seconds=5))
    await buffer.queue_message(incoming(second=4))
    await buffer.queue_message(incoming(second=1))
    await buffer.queue_message(incoming("text", second=3, text="第一件"))
    await start()
    clock[0] += timedelta(minutes=3)
    await process()
    page = await service.get_draft_list(20)
    assert page.total_count == 2
    first, second = sorted(page.list_data, key=lambda item: item.received_at)
    assert not first.collecting and not second.collecting
    assert len((await service.get_draft(first.id)).photos) == 1
    assert (await service.get_draft(first.id)).messages[-1].text == "第一件"
    assert await active_session().scalar(select(model.BatchIssueTable.id)) is None


async def test_buffer_silence_does_not_close_collection_and_later_text_is_kept(db, clock):
    await start()
    first = await buffer.queue_message(incoming(second=1))
    clock[0] += timedelta(minutes=3)
    await process()
    await buffer.queue_message(incoming("text", second=5, text="稍後補充"))
    clock[0] += timedelta(minutes=3)
    await process()
    draft = (await service.get_draft_list(20)).list_data[0]
    assert draft.collecting and len((await service.get_draft(draft.id)).messages) == 2
    assert (await service.get_draft(draft.id)).messages[0].id == first.message_id


async def test_buffer_new_arrivals_extend_wait_without_creating_a_job_per_message(db, clock):
    await start()
    clock[0] += timedelta(seconds=170)
    await buffer.queue_message(incoming(second=1))
    clock[0] += timedelta(seconds=10)
    await process()
    assert (await service.get_draft_list(20)).total_count == 0
    clock[0] += timedelta(seconds=170)
    await process()
    assert (await service.get_draft_list(20)).total_count == 1
    jobs = list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name == "product_drafts.buffer")))
    assert len(jobs) <= 2


async def test_buffer_equal_image_text_time_preserves_unassigned_content(db, clock):
    await start()
    image = await buffer.queue_message(incoming(second=1))
    text = await buffer.queue_message(incoming("text", second=1, text="同毫秒內容"))
    clock[0] += timedelta(minutes=3)
    await process()
    assert (await service.get_draft_list(20)).total_count == 0
    pending = list(await active_session().scalars(select(model.BufferedEventTable)))
    assert len(pending) == 2 and all(item.status == "issue" for item in pending)
    assert {str(item.message_id) for item in pending} == {image.message_id, text.message_id}
    assert await active_session().scalar(select(model.MessageTable.text).where(
        model.MessageTable.id == UUID(text.message_id))) == "同毫秒內容"


async def test_buffer_late_boundary_message_is_retained_without_rewriting_drafts(db, clock):
    await start()
    await buffer.queue_message(incoming(second=1))
    await buffer.queue_message(incoming(second=4))
    clock[0] += timedelta(minutes=3)
    await process()
    late = await buffer.queue_message(incoming("text", second=2, text="保留待確認"))
    clock[0] += timedelta(minutes=3)
    await process()
    assert (await service.get_draft_list(20)).total_count == 1
    item = await active_session().scalar(select(model.BufferedEventTable))
    assert item.status == "issue" and str(item.message_id) == late.message_id


async def test_buffer_duplicate_and_other_sources_do_not_extend_current_source_wait(db, clock):
    await start()
    image = incoming(second=1)
    await buffer.queue_message(image)
    clock[0] += timedelta(seconds=170)
    assert (await buffer.queue_message(image)).duplicate
    await buffer.queue_control("group-b", "start", BASE)
    await buffer.queue_message(incoming(source="group-b", second=2))
    clock[0] += timedelta(seconds=10)
    await process()
    assert (await service.get_draft_list(20, source_key="group-a")).total_count == 1
    assert (await service.get_draft_list(20, source_key="group-b")).total_count == 0
