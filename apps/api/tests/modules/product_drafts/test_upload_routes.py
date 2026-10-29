from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import photos
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR, ID, info

pytestmark = pytest.mark.asyncio


async def test_upload_route_requires_login_and_version(client, set_current_users, monkeypatch):
    uploading = AsyncMock(return_value=info(version=2))
    monkeypatch.setattr(photos, "upload_photos", uploading)
    path = f"/api/product-drafts/{ID}/photos"
    assert (await client.post(path, data={"version": "1"},
                              files={"files": ("a.png", b"image")})).status_code == 401
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    assert (await client.post(path, files={"files": ("a.png", b"image")})).status_code == 422
    result = await client.post(path, data={"version": "1"},
                               files={"files": ("a.png", b"image")})
    assert result.status_code == 200 and result.json()["version"] == 2
    assert uploading.call_args.args[0:2] == (ID, 1)
    assert uploading.call_args.args[-1]["username"] == "staff"
