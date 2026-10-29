from unittest.mock import AsyncMock

import pytest

from modules.line_collection import service
from modules.line_collection.schema import SourceInfo, SourceList
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR

pytestmark = pytest.mark.asyncio


async def test_sources_are_available_to_staff(client, set_current_users, monkeypatch):
    listing = AsyncMock(return_value=SourceList(list_data=[
        SourceInfo(source_key="line:group-a", name="供應商"),
    ]))
    monkeypatch.setattr(service, "list_sources", listing)
    assert (await client.get("/api/line/sources")).status_code == 401
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    result = await client.get("/api/line/sources")
    assert result.status_code == 200
    assert result.json()["list_data"] == [{"source_key": "line:group-a", "name": "供應商"}]
    assert (await client.patch("/api/line/groups/any", json={"enabled": True})).status_code == 403
