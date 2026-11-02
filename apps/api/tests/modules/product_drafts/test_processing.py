from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import rounds, service
from modules.product_drafts.schema import DraftProcessingInfo
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR, incoming

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
async def test_receiving_is_not_reported_as_background_processing(db):
    await rounds.receive_message(incoming(second=1))
    assert (await service.get_draft_list(20)).total_count == 0
    assert not (await service.processing_state("group-a")).processing
    assert not (await service.processing_state()).processing
    assert not (await service.processing_state("group-b")).processing
