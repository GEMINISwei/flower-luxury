from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from modules.product_drafts.quote_schema import DraftQuoteUpdate

from modules.product_drafts import collection, draft_quotes, photos, review, service, storage
from modules.product_drafts.schema import VersionRequest
from modules.products import quotes
from modules.vendors.public import VendorTable
from shared.http.errors import LangException
from tests.modules.product_drafts.helpers import ACTOR, image_bytes, incoming
from tests.modules.product_drafts.test_integration import count_products, prepared_draft

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def vendor(country="TW"):
    return await VendorTable.create({"name": "報價廠商", "country": country,
                                     "is_active": True, "country_locked": False})


async def test_draft_quotes_validate_and_reject_stale_updates(db):
    first = await collection.ingest_message(incoming())
    draft = await service.get_draft(first.draft_id)
    company = await vendor()
    form = DraftQuoteUpdate(version=draft.version, vendor_id=str(company["id"]),
                            original_amount="1200", note="手動詢價")
    added = await draft_quotes.save_quote(draft.id, form, ACTOR)
    assert len(added.quotes) == 1 and added.quotes[0].original_amount == Decimal(1200)
    assert not (await VendorTable.find_by_id(company["id"]))["country_locked"]
    with pytest.raises(LangException) as error:
        await draft_quotes.save_quote(draft.id, form, ACTOR)
    assert error.value.status_code == 409
    with pytest.raises(LangException):
        await draft_quotes.save_quote(draft.id, form.model_copy(update={
            "version": added.version, "original_amount": Decimal("1.01")}), ACTOR,
            quote_id=added.quotes[0].id)
    changed = await draft_quotes.save_quote(draft.id, form.model_copy(update={
        "version": added.version, "original_amount": Decimal(1500)}), ACTOR,
        quote_id=added.quotes[0].id)
    assert changed.quotes[0].original_amount == Decimal(1500)
    with pytest.raises(LangException):
        await draft_quotes.save_quote(draft.id, form.model_copy(update={
            "version": changed.version}), ACTOR)
    cleared = await draft_quotes.delete_quote(draft.id, changed.quotes[0].id,
                                              VersionRequest(version=changed.version))
    assert cleared.quotes == []


async def test_approval_imports_quotes_atomically(db, monkeypatch, tmp_path):
    from modules.products import photos as product_photos

    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")
    draft = await prepared_draft()
    company = await vendor()
    draft = await draft_quotes.save_quote(draft.id, DraftQuoteUpdate(version=draft.version,
        vendor_id=str(company["id"]), original_amount="1200"), ACTOR)
    before = await count_products()
    real = review.create_quote
    monkeypatch.setattr(review, "create_quote", AsyncMock(side_effect=RuntimeError("fail")))
    with pytest.raises(RuntimeError):
        await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert await count_products() == before
    assert len((await service.get_draft(draft.id)).quotes) == 1
    monkeypatch.setattr(review, "create_quote", real)
    result = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    saved = await quotes.get_quotes(result.product_id)
    assert saved.count == 1 and saved.list_data[0].original_amount == Decimal(1200)
    assert (await VendorTable.find_by_id(company["id"]))["country_locked"]


async def test_draft_cny_quote_does_not_require_rate_until_approval(db, monkeypatch, tmp_path):
    from modules.products import photos as product_photos

    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")
    first = await collection.ingest_message(incoming())
    await photos.complete_photo(first.message_id, image_bytes(), "original.png")
    draft = await service.get_draft(first.draft_id)
    company = await vendor("CN")
    draft = await draft_quotes.save_quote(draft.id, DraftQuoteUpdate(version=draft.version,
        vendor_id=str(company["id"]), original_amount="12.34"), ACTOR)
    assert draft.quotes[0].original_amount == Decimal("12.34")
