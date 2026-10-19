from unittest.mock import AsyncMock

import pytest
from modules.brands import service as brands
from modules.brands.schema import BrandList
from modules.products import photos, service
from modules.products.schema import ProductList

from tests.modules.helpers import authenticate


@pytest.fixture(autouse=True)
def people(set_current_users):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/brands/"), ("POST", "/api/brands/"),
    ("GET", "/api/products/?limit=20"), ("POST", "/api/products/"),
    ("GET", "/api/products/photos/11111111-1111-4111-8111-111111111111/file"),
])
async def test_catalog_routes_require_login(client, method, path):
    result = await client.request(method, path, json={})
    assert result.status_code == 401


@pytest.mark.asyncio
async def test_staff_can_use_catalog_routes(client, monkeypatch):
    authenticate(client, "staff")
    monkeypatch.setattr(brands, "get_brands", AsyncMock(return_value=BrandList(list_data=[], count=0)))
    monkeypatch.setattr(service, "get_product_list", AsyncMock(return_value=ProductList(
        list_data=[], total_count=0, has_next=False, has_previous=False,
    )))
    assert (await client.get("/api/brands/")).status_code == 200
    assert (await client.get("/api/products/?limit=20")).status_code == 200


@pytest.mark.asyncio
async def test_photo_file_requires_login_and_disables_caching(client, tmp_path, monkeypatch):
    path = tmp_path / "photo.webp"
    path.write_bytes(b"webp")
    monkeypatch.setattr(photos, "photo_path", AsyncMock(return_value=path))
    url = "/api/products/photos/11111111-1111-4111-8111-111111111111/file"
    assert (await client.get(url)).status_code == 401
    authenticate(client, "staff")
    result = await client.get(url)
    assert result.status_code == 200 and result.content == b"webp"
    assert "no-store" in result.headers["cache-control"]
