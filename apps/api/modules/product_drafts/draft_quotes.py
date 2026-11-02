from uuid import uuid4

from modules.products.public import price_quote
from modules.vendors.public import VendorError, lock_vendor
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found

from . import model
from .errors import DraftError
from .quote_schema import DraftQuoteUpdate
from .rules import check_version
from .schema import DraftInfo, DraftQuoteInfo, SaleSelection, VersionRequest
from .service import _bump, get_draft


async def save_quote(id: str, form: DraftQuoteUpdate, actor: CurrentUser,
                     *, quote_id: str | None = None) -> DraftInfo:
    async with transaction():
        row = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        check_version(row.version, form.version)
        existing = [DraftQuoteInfo.model_validate(item) for item in row.quotes or []]
        if quote_id and not any(item.id == quote_id for item in existing):
            raise LangException(404, DraftError.NOT_FOUND)
        if any(item.vendor_id == form.vendor_id and item.id != quote_id for item in existing):
            raise LangException(409, DraftError.DUPLICATE_QUOTE)
        vendor = await lock_vendor(form.vendor_id)
        if not vendor.is_active:
            raise LangException(409, VendorError.INACTIVE)
        price_quote(form.original_amount, form.exchange_rate)
        quote = DraftQuoteInfo(id=quote_id or str(uuid4()), vendor_id=form.vendor_id,
                              original_amount=form.original_amount,
                              exchange_rate=form.exchange_rate,
                              note=form.note)
        row.quotes = [item.model_dump(mode="json") for item in existing if item.id != quote_id]
        row.quotes = [*row.quotes, quote.model_dump(mode="json")]
        _bump(row, actor)
        await active_session().flush()
        return await get_draft(id)


async def delete_quote(id: str, quote_id: str, form: VersionRequest) -> DraftInfo:
    async with transaction():
        row = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        check_version(row.version, form.version)
        quotes = row.quotes or []
        if not any(item["id"] == quote_id for item in quotes):
            raise LangException(404, DraftError.NOT_FOUND)
        row.quotes = [item for item in quotes if item["id"] != quote_id]
        if row.selected_quote_id == quote_id:
            row.selected_quote_id = None
        _bump(row)
        await active_session().flush()
        return await get_draft(id)


async def select_sale(id: str, form: SaleSelection, actor: CurrentUser) -> DraftInfo:
    async with transaction():
        row = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        check_version(row.version, form.version)
        if form.quote_id and not any(item["id"] == form.quote_id for item in row.quotes or []):
            raise LangException(409, DraftError.INVALID_SALE_QUOTE)
        row.selected_quote_id = form.quote_id
        _bump(row, actor)
        await active_session().flush()
        return await get_draft(id)
