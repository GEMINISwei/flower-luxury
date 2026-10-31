from datetime import datetime
from types import SimpleNamespace

from modules.brands.public import get_brands
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session, release_connection
from shared.db.transaction import transaction
from shared.http.errors import LangException, resolve_text

from . import model
from .errors import DraftError
from .prefill_config import get_env
from .prefill_prompt import BASE_PROMPT
from .prefill_rules import build_input, output_schema, parse_prefill
from .prefill_schema import PrefillPreview, PrefillSettingsInfo, PrefillSettingsUpdate
from .prefill_transport import PrefillTransportError, generate_prefill
from .schema import DraftFields


async def get_settings() -> PrefillSettingsInfo:
    row = await model.prefill_settings_row()
    return PrefillSettingsInfo(supplement=row.supplement if row else "",
                              revision=row.revision if row else 0,
                              configured=get_env().prefill_configured,
                              base_prompt=resolve_text(BASE_PROMPT))


async def update_settings(form: PrefillSettingsUpdate, actor: CurrentUser) -> PrefillSettingsInfo:
    async with transaction():
        if not await model.write_prefill_settings(form.supplement, form.revision, actor["id"]):
            raise LangException(409, DraftError.STALE)
        return await get_settings()


async def preview(form: PrefillPreview) -> DraftFields:
    if not get_env().prefill_configured:
        raise LangException(503, DraftError.PREFILL_UNAVAILABLE)
    brands = await get_brands()
    options = [{"id": brand.id, "name": brand.name} for brand in brands.list_data]
    messages = [SimpleNamespace(kind="text", text=form.text, occurred_at=datetime(2000, 1, 1),
                                sequence=1)]
    try:
        content = build_input(messages, options, form.supplement)
        await release_connection()
        response = await generate_prefill(BASE_PROMPT.zh, content, output_schema())
        result = parse_prefill(response, {item["id"] for item in options})
        await active_session().flush()
        return result
    except (PrefillTransportError, ValueError) as error:
        raise LangException(502, DraftError.PREFILL_UNAVAILABLE) from error
