from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import photos
from modules.product_drafts.schema import StoredFile
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR, ID


@pytest.mark.asyncio
async def test_draft_variant_routes_validate_size_and_require_login(
    client, set_current_users, monkeypatch, tmp_path,
):
    path = tmp_path / "preview.webp"
    path.write_bytes(b"preview")
    reading = AsyncMock(return_value=StoredFile(
        path=path, media_type="image/webp", filename="preview.webp",
    ))
    monkeypatch.setattr(photos, "read_photo", reading)
    url = f"/api/product-drafts/photos/{ID}/file"
    for size in ("128", "320", "640", "full"):
        assert (await client.get(url, params={"size": size})).status_code == 401
    assert reading.await_count == 0
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    for size in ("128", "320", "640", "full"):
        result = await client.get(url, params={"size": size})
        assert result.status_code == 200 and result.content == b"preview"
        assert result.headers["cache-control"] == "private, no-store"
        assert result.headers["vary"] == "Cookie"
        assert reading.call_args.kwargs["size"] == size
    assert (await client.get(url, params={"size": "2560"})).status_code == 422
