from fastapi import APIRouter, Depends

from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.schema import UuidText

from . import quotes
from .quote_schema import QuoteCreate, QuoteInfo, QuoteList, QuoteUpdate

router = APIRouter(prefix="/products/{id}/quotes", tags=["product quotes"])


@router.get("")
async def get_quotes_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> QuoteList:
    return await quotes.get_quotes(id)


@router.post("")
async def create_quote_route(
    id: UuidText, form_data: QuoteCreate, actor: CurrentUser = Depends(check_user_permission()),
) -> QuoteInfo:
    return await quotes.create_quote(id, form_data, actor)


@router.patch("/{quote_id}")
async def update_quote_route(
    id: UuidText, quote_id: UuidText, form_data: QuoteUpdate,
    actor: CurrentUser = Depends(check_user_permission()),
) -> QuoteInfo:
    return await quotes.update_quote(id, quote_id, form_data, actor)


@router.delete("/{quote_id}")
async def delete_quote_route(
    id: UuidText, quote_id: UuidText, actor: CurrentUser = Depends(check_user_permission()),
) -> QuoteInfo:
    return await quotes.delete_quote(id, quote_id, actor)
