from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import collection, pending
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR, ID, info

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("path", [
    f"/api/product-drafts/{ID}/complete",
    f"/api/product-drafts/{ID}/pending/{ID}/accept",
    f"/api/product-drafts/{ID}/pending/{ID}/ignore",
])
async def test_complete_and_pending_routes_require_login_and_pass_version(
    client, set_current_users, monkeypatch, path,
):
    assert (await client.post(path, json={"version": 1})).status_code == 401
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    handlers = {name: AsyncMock(return_value=info(version=2)) for name in
                ("complete_draft", "accept_message", "ignore_message")}
    monkeypatch.setattr(collection, "complete_draft", handlers["complete_draft"])
    monkeypatch.setattr(pending, "accept_message", handlers["accept_message"])
    monkeypatch.setattr(pending, "ignore_message", handlers["ignore_message"])
    result = await client.post(path, json={"version": 1})
    assert result.status_code == 200 and result.json()["version"] == 2
    called = [handler for handler in handlers.values() if handler.await_count]
    assert len(called) == 1 and called[0].await_args.args[-2].version == 1
