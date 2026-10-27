from unittest.mock import AsyncMock

import pytest

from modules.products import photos, router
from modules.products.schema import PhotoFile, PhotoList
from tests.modules.helpers import authenticate

ID = "11111111-1111-4111-8111-111111111111"


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("GET", f"/api/products/{ID}/photos"), ("POST", f"/api/products/{ID}/photos"),
    ("PATCH", f"/api/products/{ID}/photos/main"),
    ("DELETE", f"/api/products/{ID}/photos/{ID}"),
    ("GET", f"/api/products/photos/{ID}/file"),
])
async def test_photo_routes_require_login(client, method, path):
    assert (await client.request(method, path)).status_code == 401


@pytest.mark.asyncio
async def test_photo_display_requires_login_and_disables_cache(
    client, set_current_users, monkeypatch, tmp_path,
):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    path = tmp_path / "display.webp"
    path.write_bytes(b"display")
    monkeypatch.setattr(photos, "photo_path", AsyncMock(return_value=PhotoFile(path=path)))
    result = await client.get(f"/api/products/photos/{ID}/file")
    assert result.status_code == 200 and result.content == b"display"
    assert result.headers["content-type"] == "image/webp"
    assert result.headers["cache-control"] == "private, no-store"
    assert result.headers["vary"] == "Cookie"


@pytest.mark.asyncio
async def test_upload_releases_read_connection_before_processing(
    client, set_current_users, monkeypatch,
):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    order = []

    async def release():
        order.append("release")

    async def upload(*args):
        order.append("upload")
        return PhotoList(list_data=[], count=0)

    monkeypatch.setattr(router, "release_connection", release)
    monkeypatch.setattr(photos, "upload_photos", upload)
    result = await client.post(f"/api/products/{ID}/photos", files=[("files", ("a.png", b"test"))])
    assert result.status_code == 200 and order == ["release", "upload"]
