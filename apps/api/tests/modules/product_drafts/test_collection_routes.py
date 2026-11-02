from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import collection_schema, rounds
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR, ID, info

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(("method", "path"), [
    ("GET", "/api/product-drafts/collections/current?source_key=group-a"),
    ("POST", f"/api/product-drafts/collections/{ID}/complete"),
    ("POST", f"/api/product-drafts/{ID}/finalize"),
])
async def test_collection_routes_require_login(client, method, path):
    assert (await client.request(method, path, json={"version": 1})).status_code == 401


async def test_staff_can_complete_and_finalize_with_operator(
    client, set_current_users, monkeypatch,
):
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    complete = AsyncMock(return_value=collection_schema.CollectionInfo(
        id=ID, source_key="group-a", status="confirmation", message_count=2))
    finalize = AsyncMock(return_value=info(version=2))
    monkeypatch.setattr(rounds, "complete_collection", complete)
    monkeypatch.setattr(rounds, "finalize_draft", finalize)
    result = await client.post(f"/api/product-drafts/collections/{ID}/complete")
    assert result.status_code == 200 and result.json()["status"] == "confirmation"
    complete.assert_awaited_once_with(ID)
    result = await client.post(f"/api/product-drafts/{ID}/finalize", json={"version": 1})
    assert result.status_code == 200 and result.json()["version"] == 2
    assert finalize.call_args.args[-1]["username"] == "staff"
