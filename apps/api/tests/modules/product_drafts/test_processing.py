from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from modules.product_drafts import buffer, service
from modules.product_drafts.schema import DraftProcessingInfo
from shared.jobs.contracts import Job
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR, BASE, incoming

pytestmark = pytest.mark.asyncio


async def test_processing_route_requires_login_and_scopes_source(client, set_current_users,
                                                                monkeypatch):
    assert (await client.get("/api/product-drafts/processing")).status_code == 401
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    state = AsyncMock(return_value=DraftProcessingInfo(processing=True))
    monkeypatch.setattr(service, "processing_state", state)
    result = await client.get("/api/product-drafts/processing?source_key=group-a")
    assert result.status_code == 200 and result.json() == {"processing": True}
    state.assert_awaited_once_with("group-a")


@pytest.mark.integration
async def test_processing_state_tracks_buffer_before_any_draft_exists(db, monkeypatch):
    now = [BASE]
    monkeypatch.setattr(buffer, "utc_now", lambda: now[0])
    await buffer.queue_message(incoming(second=1))
    assert (await service.get_draft_list(20)).total_count == 0
    assert (await service.processing_state("group-a")).processing
    assert (await service.processing_state()).processing
    assert not (await service.processing_state("group-b")).processing
    now[0] += timedelta(minutes=3)
    await buffer.process_buffer(Job(id=uuid4(), task_name="product_drafts.buffer",
                                   payload={"source_key": "group-a"}, attempts=1))
    assert not (await service.processing_state("group-a")).processing
