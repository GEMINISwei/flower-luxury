from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from modules.line_collection import service
from modules.line_collection.config import LineSettings
from modules.line_collection.schema import GroupList, WebhookResult
from tests.modules.helpers import authenticate
from tests.modules.line_collection.test_rules import SECRET, signature
from tests.modules.product_drafts.helpers import ACTOR

pytestmark = pytest.mark.asyncio


async def test_webhook_rejects_invalid_signature_and_disabled_configuration(client, monkeypatch):
    from app.server import app

    monkeypatch.setattr(app.state.env, "line_channel_secret", "")
    monkeypatch.setattr(app.state.env, "line_channel_access_token", "")
    assert (await client.post("/api/line/webhook", content=b'{"events":[]}')).status_code == 503
    settings = LineSettings(
        line_channel_secret=SecretStr(SECRET), line_channel_access_token=SecretStr("token"))
    monkeypatch.setattr(app.state, "env", settings)
    result = await client.post("/api/line/webhook", content=b'{"events":[]}',
                               headers={"x-line-signature": "bad"})
    assert result.status_code == 401
    result = await client.post("/api/line/webhook", content=b'{"events":[]}',
                               headers={"x-line-signature": signature(b'{"events":[]}')})
    assert result.status_code == 200 and result.json() == {"accepted": 0}


async def test_webhook_returns_success_only_after_service_completes(client, monkeypatch):
    from app.server import app

    settings = LineSettings(
        line_channel_secret=SecretStr(SECRET), line_channel_access_token=SecretStr("token"))
    monkeypatch.setattr(app.state, "env", settings)
    receive = AsyncMock(return_value=WebhookResult(accepted=1))
    monkeypatch.setattr(service, "receive_webhook", receive)
    result = await client.post("/api/line/webhook", content=b"raw",
                               headers={"x-line-signature": "signed"})
    assert result.status_code == 200 and receive.call_args.args[:2] == (b"raw", "signed")


async def test_group_management_requires_manager(client, set_current_users, monkeypatch):
    listing = AsyncMock(return_value=GroupList(list_data=[], has_next=False,
                                             has_previous=False, total_count=0))
    monkeypatch.setattr(service, "list_groups", listing)
    assert (await client.get("/api/line/groups")).status_code == 401
    set_current_users({"staff": ACTOR, "manager": {**ACTOR, "permissions": ["*"]}})
    authenticate(client, "staff")
    assert (await client.get("/api/line/groups")).status_code == 403
    result = await client.patch("/api/line/groups/group-a", json={"enabled": True})
    assert result.status_code == 403
    assert (await client.post("/api/line/groups/group-a/stop")).status_code == 403
    authenticate(client, "manager")
    assert (await client.get("/api/line/groups")).status_code == 200
    listing.assert_awaited_once()
