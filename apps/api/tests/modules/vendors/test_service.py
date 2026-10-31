from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from modules.vendors import service
from modules.vendors.schema import VendorCreate
from shared.http.errors import LangException

VENDOR = "11111111-1111-4111-8111-111111111111"


class ConstraintError(Exception):
    sqlstate: str


@asynccontextmanager
async def isolated_transaction():
    yield


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
            await service.create_vendor(VendorCreate(name="Buyer"))
        assert result.value.status_code == code
    else:
        with pytest.raises(IntegrityError):
            await service.create_vendor(VendorCreate(name="Buyer"))


@pytest.mark.asyncio
async def test_deleting_quoted_vendor_deactivates_without_deleting(monkeypatch):
    data = {"id": VENDOR, "name": "Buyer", "is_active": True,
            "has_quotes": True, "note": None}
    row = SimpleNamespace(**data)
    row.to_dict = lambda: {**data, "is_active": row.is_active}
    session = MagicMock()
    session.flush, session.delete = AsyncMock(), AsyncMock()
    monkeypatch.setattr(service, "transaction", isolated_transaction)
    monkeypatch.setattr(service, "lock_vendor", AsyncMock(return_value=row))
    monkeypatch.setattr(service, "active_session", lambda: session)
    result = await service.delete_vendor(VENDOR)
    assert result.is_active is False and result.has_quotes is True
    session.delete.assert_not_awaited()
