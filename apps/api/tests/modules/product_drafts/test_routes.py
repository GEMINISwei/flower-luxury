from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import photos, review, service
from modules.product_drafts.errors import DraftError
from modules.product_drafts.schema import ApprovalInfo, DraftList, StoredFile
from shared.http.errors import LangException
from tests.modules.helpers import authenticate
from tests.modules.product_drafts.helpers import ACTOR, BASE, ID, info

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/product-drafts/"), ("GET", "/api/product-drafts/messages"),
    ("GET", f"/api/product-drafts/{ID}"), ("PATCH", f"/api/product-drafts/{ID}"),
    ("DELETE", f"/api/product-drafts/{ID}"), ("POST", f"/api/product-drafts/{ID}/approve"),
    ("PATCH", f"/api/product-drafts/{ID}/photos/order"),
    ("PATCH", f"/api/product-drafts/{ID}/photos/main"),
    ("DELETE", f"/api/product-drafts/{ID}/photos/{ID}"),
    ("POST", f"/api/product-drafts/messages/{ID}/move"),
    ("GET", f"/api/product-drafts/photos/{ID}/file"),
    ("GET", f"/api/product-drafts/photos/{ID}/download"),
])
async def test_draft_routes_require_login(client, method, path):
    assert (await client.request(method, path, json={})).status_code == 401


async def test_staff_can_edit_and_approve_drafts(client, set_current_users, monkeypatch):
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    update = AsyncMock(return_value=info(version=2))
    approval = ApprovalInfo(draft_id=ID, product_id=ID, sku="LX20261028ABCDE",
                            reviewed_by=ACTOR["id"], reviewer_name="staff", reviewed_at=BASE)
    approve = AsyncMock(return_value=approval)
    monkeypatch.setattr(service, "update_draft", update)
    monkeypatch.setattr(review, "approve_draft", approve)
    result = await client.patch(f"/api/product-drafts/{ID}", json={"version": 1, "fields": {}})
    assert result.status_code == 200 and result.json()["version"] == 2
    result = await client.post(f"/api/product-drafts/{ID}/approve", json={"version": 2})
    assert result.status_code == 200 and result.json()["product_id"] == ID
    assert approve.call_args.args[-1]["username"] == "staff"


async def test_staff_can_list_drafts(client, set_current_users, monkeypatch):
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    monkeypatch.setattr(service, "get_draft_list", AsyncMock(return_value=DraftList(
        list_data=[], has_next=False, has_previous=False, total_count=0,
    )))
    result = await client.get("/api/product-drafts/?limit=20")
    assert result.status_code == 200 and result.json()["total_count"] == 0


@pytest.mark.parametrize("lang,expected", [("zh", "資料已變更"), ("en", "changed")])
async def test_draft_conflicts_follow_request_language(
    client, set_current_users, monkeypatch, lang, expected,
):
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")

    async def conflict(*args):
        raise LangException(409, DraftError.STALE)

    monkeypatch.setattr(service, "update_draft", conflict)
    result = await client.patch(f"/api/product-drafts/{ID}", json={"version": 1, "fields": {}},
                                headers={"Accept-Language": lang})
    assert result.status_code == 409 and expected in result.json()["detail"]


@pytest.mark.parametrize("suffix,media", [("file", "image/webp"), ("download", "image/png")])
async def test_draft_photo_routes_disable_cache(
    client, set_current_users, monkeypatch, tmp_path, suffix, media,
):
    set_current_users({"staff": ACTOR})
    authenticate(client, "staff")
    path = tmp_path / "photo"
    path.write_bytes(b"photo")
    monkeypatch.setattr(photos, "read_photo", AsyncMock(return_value=StoredFile(
        path=path, media_type=media, filename="photo.png",
    )))
    result = await client.get(f"/api/product-drafts/photos/{ID}/{suffix}")
    assert result.status_code == 200 and result.content == b"photo"
    assert result.headers["cache-control"] == "private, no-store"
    assert result.headers["vary"] == "Cookie"
