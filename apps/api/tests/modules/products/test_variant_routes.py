from unittest.mock import AsyncMock

import pytest

from modules.products import photos
from modules.products.schema import PhotoFile
from tests.modules.helpers import authenticate
from tests.modules.products.test_photo_routes import ID


@pytest.mark.asyncio
async def test_product_variant_routes_validate_size_and_require_login(
    client, set_current_users, monkeypatch, tmp_path,
):
    path = tmp_path / "preview.webp"
    path.write_bytes(b"preview")
    reading = AsyncMock(return_value=PhotoFile(path=path))
    monkeypatch.setattr(photos, "photo_path", reading)
    url = f"/api/products/photos/{ID}/file"
    for size in ("128", "320", "640", "full"):
        assert (await client.get(url, params={"size": size})).status_code == 401
    assert reading.await_count == 0
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    for size in ("128", "320", "640", "full"):
        result = await client.get(url, params={"size": size})
        assert result.status_code == 200 and result.content == b"preview"
        assert result.headers["content-type"] == "image/webp"
        assert result.headers["cache-control"] == "private, no-store"
        assert result.headers["vary"] == "Cookie"
        assert reading.call_args.kwargs["size"] == size
    for size in ("0", "2560", "../originals", "999999"):
        assert (await client.get(url, params={"size": size})).status_code == 422
