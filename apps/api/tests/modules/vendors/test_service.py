from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from modules.vendors import service
from modules.vendors.schema import VendorCreate, VendorUpdate
from shared.http.errors import LangException

VENDOR = "11111111-1111-4111-8111-111111111111"


class ConstraintError(Exception):
    sqlstate: str


@asynccontextmanager
async def isolated_transaction():
    yield


@pytest.mark.asyncio
async def test_country_change_is_rejected_before_writing(monkeypatch):
    session = MagicMock()
    session.flush = AsyncMock()
    row = SimpleNamespace(country="TW", country_locked=True)
    monkeypatch.setattr(service, "transaction", isolated_transaction)
    monkeypatch.setattr(service, "lock_vendor", AsyncMock(return_value=row))
    monkeypatch.setattr(service, "active_session", lambda: session)
    with pytest.raises(LangException) as error:
        await service.update_vendor(VENDOR, VendorUpdate(
            name="Buyer", country="CN", is_active=True,
        ))
    assert error.value.status_code == 409 and row.country == "TW"
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("state,code", [("23505", 409), ("23503", None)])
async def test_create_vendor_translates_only_unique_violations(monkeypatch, state, code):
    cause = ConstraintError("database constraint")
    cause.sqlstate = state
    error = IntegrityError("insert", {}, cause)
    monkeypatch.setattr(service, "transaction", isolated_transaction)
    monkeypatch.setattr(service.VendorTable, "create", AsyncMock(side_effect=error))
    if code:
        with pytest.raises(LangException) as result:
            await service.create_vendor(VendorCreate(name="Buyer", country="TW"))
        assert result.value.status_code == code
    else:
        with pytest.raises(IntegrityError):
            await service.create_vendor(VendorCreate(name="Buyer", country="TW"))


@pytest.mark.asyncio
async def test_deleting_quoted_vendor_deactivates_without_deleting(monkeypatch):
    data = {"id": VENDOR, "name": "Buyer", "country": "TW", "is_active": True,
            "country_locked": True, "note": None}
    row = SimpleNamespace(**data)
    row.to_dict = lambda: {**data, "is_active": row.is_active}
    session = MagicMock()
    session.flush, session.delete = AsyncMock(), AsyncMock()
    monkeypatch.setattr(service, "transaction", isolated_transaction)
    monkeypatch.setattr(service, "lock_vendor", AsyncMock(return_value=row))
    monkeypatch.setattr(service, "active_session", lambda: session)
    result = await service.delete_vendor(VENDOR)
    assert result.is_active is False and result.country_locked is True
    session.delete.assert_not_awaited()
