from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import prefill_settings
from modules.product_drafts.prefill_schema import PrefillResult, PrefillSettingsInfo
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR

pytestmark = pytest.mark.asyncio


async def test_prefill_settings_require_manager_and_preview_is_read_only(
    client, set_current_users, monkeypatch,
):
    set_current_users({"staff": ACTOR, "manager": {**ACTOR, "permissions": ["*"]}})
    read = AsyncMock(return_value=PrefillSettingsInfo(supplement="", revision=0,
                                                    configured=False, base_prompt="基礎規則"))
    preview = AsyncMock(return_value=PrefillResult(name="預覽"))
    monkeypatch.setattr(prefill_settings, "get_settings", read)
    monkeypatch.setattr(prefill_settings, "preview", preview)
    assert (await client.get("/api/draft-prefill/settings")).status_code == 401
    authenticate(client, "staff")
    assert (await client.get("/api/draft-prefill/settings")).status_code == 403
    assert (await client.patch("/api/draft-prefill/settings", json={
        "supplement": "規則", "revision": 0})).status_code == 403
    assert (await client.post("/api/draft-prefill/preview", json={
        "text": "文字", "supplement": "規則"})).status_code == 403
    authenticate(client, "manager")
    assert (await client.get("/api/draft-prefill/settings")).json()["configured"] is False
    result = await client.post("/api/draft-prefill/preview", json={
        "text": "文字", "supplement": "規則"})
    assert result.status_code == 200 and result.json()["name"] == "預覽"
    assert preview.call_args.args[0].text == "文字"


async def test_manual_prefill_and_global_rate_routes_are_removed(client):
    assert (await client.post("/api/product-drafts/11111111-1111-4111-8111-111111111111/prefill",
                              json={"version": 1})).status_code == 404
    assert (await client.get("/api/exchange-rates/settings")).status_code == 404
