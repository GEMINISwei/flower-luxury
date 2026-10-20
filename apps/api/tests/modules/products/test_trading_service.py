from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.products import quotes, sales
from modules.products.quote_schema import QuoteCreate, SaleCreate
from shared.auth.contracts import CurrentUser
from shared.http.errors import LangException

ACTOR: CurrentUser = {"id": "staff", "username": "staff", "permissions": [],
                      "is_disabled": False, "auth_version": 1}
PRODUCT = "11111111-1111-4111-8111-111111111111"
QUOTE = "22222222-2222-4222-8222-222222222222"


@asynccontextmanager
async def isolated_transaction():
    yield


@pytest.mark.asyncio
async def test_inactive_vendor_rejects_quote_before_reading_rate(monkeypatch):
    rate = AsyncMock()
    monkeypatch.setattr(quotes, "transaction", isolated_transaction)
    monkeypatch.setattr(quotes, "lock_product", AsyncMock())
    monkeypatch.setattr(
        quotes, "lock_vendor", AsyncMock(return_value=SimpleNamespace(is_active=False)),
    )
    monkeypatch.setattr(quotes, "get_settings", rate)
    with pytest.raises(LangException) as error:
        await quotes.create_quote(PRODUCT, QuoteCreate(vendor_id=QUOTE, original_amount="1"), ACTOR)
    assert error.value.status_code == 409
    rate.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("revision,cost", [(2, 100), (1, 101)])
async def test_stale_sale_rejects_without_creating_snapshot(monkeypatch, revision, cost):
    create = AsyncMock()
    monkeypatch.setattr(sales, "transaction", isolated_transaction)
    monkeypatch.setattr(
        sales, "lock_product", AsyncMock(return_value=SimpleNamespace(cost_price=cost)),
    )
    monkeypatch.setattr(
        sales, "load_quote", AsyncMock(return_value=SimpleNamespace(revision=revision)),
    )
    monkeypatch.setattr(sales.ProductSaleTable, "create", create)
    with pytest.raises(LangException) as error:
        await sales.confirm_sale(PRODUCT, SaleCreate(
            quote_id=QUOTE, quote_revision=1, cost_price=100,
        ), ACTOR)
    assert error.value.status_code == 409
    create.assert_not_awaited()


@pytest.mark.asyncio
async def test_quote_delete_rejects_historical_sale_reference(monkeypatch):
    session = MagicMock()
    session.delete = AsyncMock()
    monkeypatch.setattr(quotes, "transaction", isolated_transaction)
    monkeypatch.setattr(quotes, "lock_product", AsyncMock())
    monkeypatch.setattr(quotes, "load_quote", AsyncMock())
    monkeypatch.setattr(
        quotes, "quote_info", AsyncMock(return_value=SimpleNamespace(has_sales=True)),
    )
    monkeypatch.setattr(quotes, "active_session", lambda: session)
    with pytest.raises(LangException) as error:
        await quotes.delete_quote(PRODUCT, QUOTE, ACTOR)
    assert error.value.status_code == 409
    session.delete.assert_not_awaited()
