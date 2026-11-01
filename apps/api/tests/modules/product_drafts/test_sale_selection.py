from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from modules.product_drafts import draft_quotes, model, review, service, storage
from modules.product_drafts.quote_schema import DraftQuoteUpdate
from modules.product_drafts.schema import SaleSelection, VersionRequest
from modules.products import photos as product_photos
from modules.products import sales
from modules.products.model import ProductSaleTable
from modules.products.public import get_product
from shared.db.session import active_session
from shared.http.errors import LangException
from tests.modules.product_drafts.helpers import ACTOR, ID
from tests.modules.product_drafts.test_draft_quotes import vendor
from tests.modules.product_drafts.test_integration import count_products, prepared_draft
from tests.modules.product_drafts.test_services import ready
from tests.modules.product_drafts.test_services import state as state

pytestmark = pytest.mark.asyncio


async def test_sale_selection_rejects_missing_quote_and_stale_version_without_database(state):
    draft = await ready()
    row = state[model.DraftTable][draft.id]
    row.quotes = [{"id": ID, "vendor_id": ID, "original_amount": "100",
                   "exchange_rate": "1", "note": None}]
    chosen = await draft_quotes.select_sale(draft.id,
        SaleSelection(version=draft.version, quote_id=ID), ACTOR)
    assert chosen.selected_quote_id == ID
    with pytest.raises(LangException):
        await draft_quotes.select_sale(draft.id,
            SaleSelection(version=draft.version, quote_id=None), ACTOR)
    with pytest.raises(LangException):
        await draft_quotes.select_sale(draft.id,
            SaleSelection(version=chosen.version, quote_id=draft.id), ACTOR)
    cleared = await draft_quotes.select_sale(draft.id,
        SaleSelection(version=chosen.version, quote_id=None), ACTOR)
    assert cleared.selected_quote_id is None


@pytest.mark.integration
async def test_selected_quote_approval_saves_sale_snapshot_with_product_creation_time(db,
                                                                                   monkeypatch,
                                                                                   tmp_path):
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")
    draft = await prepared_draft()
    company = await vendor()
    draft = await draft_quotes.save_quote(draft.id, DraftQuoteUpdate(version=draft.version,
        vendor_id=str(company["id"]), original_amount="1200", exchange_rate="4.5"), ACTOR)
    draft = await draft_quotes.select_sale(draft.id,
        SaleSelection(version=draft.version, quote_id=draft.quotes[0].id), ACTOR)
    receipt = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    product = await get_product(receipt.product_id)
    saved = (await sales.get_sales(product.id)).list_data
    assert product.status == "sold" and len(saved) == 1
    assert saved[0].sold_at == product.created_at
    assert saved[0].vendor_name == company["name"]
    assert saved[0].amount_twd == 5400 and saved[0].cost_price == 3000
    assert saved[0].profit_amount == 2400 and saved[0].changed_by == ACTOR["id"]
    repeated = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert repeated.product_id == product.id
    assert len((await sales.get_sales(product.id)).list_data) == 1


@pytest.mark.integration
async def test_sale_failure_rolls_back_import_and_keeps_selected_draft(db, monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")
    draft = await prepared_draft()
    company = await vendor()
    draft = await draft_quotes.save_quote(draft.id, DraftQuoteUpdate(version=draft.version,
        vendor_id=str(company["id"]), original_amount="100"), ACTOR)
    draft = await draft_quotes.select_sale(draft.id,
        SaleSelection(version=draft.version, quote_id=draft.quotes[0].id), ACTOR)
    before = await count_products()
    monkeypatch.setattr(review, "confirm_imported_sale",
                        AsyncMock(side_effect=RuntimeError("sale failed")))
    with pytest.raises(RuntimeError):
        await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert await count_products() == before
    assert (await service.get_draft(draft.id)).selected_quote_id == draft.quotes[0].id
    assert await active_session().scalar(select(ProductSaleTable.id)) is None


@pytest.mark.integration
async def test_deleting_selected_quote_clears_selection(db):
    draft = await prepared_draft()
    company = await vendor()
    draft = await draft_quotes.save_quote(draft.id, DraftQuoteUpdate(version=draft.version,
        vendor_id=str(company["id"]), original_amount="100"), ACTOR)
    quote_id = draft.quotes[0].id
    draft = await draft_quotes.select_sale(draft.id,
        SaleSelection(version=draft.version, quote_id=quote_id), ACTOR)
    draft = await draft_quotes.delete_quote(draft.id, quote_id,
                                          VersionRequest(version=draft.version))
    assert draft.quotes == [] and draft.selected_quote_id is None
