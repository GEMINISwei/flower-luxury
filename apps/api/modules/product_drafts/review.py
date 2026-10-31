from collections.abc import AsyncIterator

from pydantic import ValidationError

from modules.products.public import (
    PreparedPhoto,
    ProductCreate,
    ProductInfo,
    QuoteCreate,
    create_imported_product,
    create_quote,
)
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.table import parse_uuid
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found

from . import model, storage
from .errors import DraftError
from .rules import check_version
from .schema import ApprovalInfo, DiscardInfo, VersionRequest


def _approval(row: model.ApprovalTable) -> ApprovalInfo:
    return ApprovalInfo(draft_id=str(row.id), product_id=str(row.product_id), sku=row.sku,
                        reviewed_by=row.reviewed_by, reviewer_name=row.reviewer_name,
                        reviewed_at=row.created_at)


async def _prepared_photos(rows: list[model.PhotoTable]) -> AsyncIterator[PreparedPhoto]:
    # 逐張讀取, 讓連續多圖不會在審核時把全部原圖同時放進記憶體。
    for row in rows:
        try:
            yield await storage.load_prepared(row)
        except OSError as error:
            raise LangException(409, DraftError.PHOTO_NOT_READY) from error


async def approve_draft(id: str, form: VersionRequest, actor: CurrentUser) -> ApprovalInfo:
    async with transaction():
        draft = await model.get_draft_row(id, lock=True)
        if draft is None:
            return _approval(ensure_found(await model.approval_for(id), DraftError.NOT_FOUND))
        check_version(draft.version, form.version)
        try:
            fields = ProductCreate.model_validate(draft.fields)
        except ValidationError as error:
            raise LangException(422, DraftError.INVALID_FIELDS) from error
        rows = await model.photos_for(id)
        if not rows or any(row.status != "ready" for row in rows):
            raise LangException(409, DraftError.PHOTO_NOT_READY)
        main_index = next((index for index, row in enumerate(rows)
                           if row.id == draft.main_photo_id), 0)

        async def import_quotes(product: ProductInfo) -> None:
            for quote in draft.quotes or []:
                await create_quote(product.id, QuoteCreate.model_validate({
                    key: quote.get(key) for key in ("vendor_id", "original_amount", "note")
                }), actor)

        product = await create_imported_product(
            fields, _prepared_photos(rows), actor, main_index=main_index,
            on_created=import_quotes,
        )
        await model.remember_approved_messages(id, product.id)
        receipt = model.ApprovalTable(
            id=draft.id, product_id=parse_uuid(product.id), sku=product.sku,
            reviewed_by=actor["id"], reviewer_name=actor["username"],
        )
        active_session().add(receipt)
        await storage.schedule_cleanup(rows)
        await active_session().delete(draft)
        await active_session().flush()
        return _approval(receipt)


async def discard_draft(id: str, form: VersionRequest, _actor: CurrentUser) -> DiscardInfo:
    async with transaction():
        draft = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        check_version(draft.version, form.version)
        await storage.schedule_cleanup(await model.photos_for(id))
        await active_session().delete(draft)
        await active_session().flush()
        return DiscardInfo(id=id)
