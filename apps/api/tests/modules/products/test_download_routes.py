from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from modules.products import photos
from modules.products.schema import OriginalPhotoFile
from tests.modules.helpers import authenticate


@pytest.mark.asyncio
async def test_original_download_requires_login_and_uses_attachment(
    client, set_current_users, tmp_path, monkeypatch,
):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    path = tmp_path / "original.heic"
    path.write_bytes(b"original heic bytes")
    monkeypatch.setattr(photos, "original_file", AsyncMock(return_value=OriginalPhotoFile(
        path=path, filename="商品原圖.heic", media_type="image/heic",
    )), raising=False)
    url = "/api/products/photos/11111111-1111-4111-8111-111111111111/download"
    assert (await client.get(url)).status_code == 401
    authenticate(client, "staff")
    result = await client.get(url)
    assert result.status_code == 200 and result.content == path.read_bytes()
    assert result.headers["content-type"] == "image/heic"
    assert result.headers["content-disposition"].startswith("attachment;")
    assert ".heic" in result.headers["content-disposition"]
    assert result.headers["cache-control"] == "private, no-store"
    assert result.headers["vary"] == "Cookie"


def test_photo_download_proxy_is_available_in_both_templates():
    root = Path(__file__).resolve().parents[5]
    for name in ["default.conf.template", "default.dev.conf.template"]:
        template = (root / "infra/nginx" / name).read_text()
        assert "/(file|download)$" in template
