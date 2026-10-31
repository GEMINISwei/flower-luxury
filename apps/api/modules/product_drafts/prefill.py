from datetime import timedelta

from modules.brands.public import get_brands
from shared.db.session import active_session, release_connection
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found
from shared.jobs.contracts import Job
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import model, prefill_settings
from .errors import DraftError
from .prefill_config import get_env
from .prefill_prompt import BASE_PROMPT
from .prefill_rules import build_input, merge_prefill, output_schema, parse_prefill
from .prefill_transport import PrefillTransportError, generate_prefill
from .rules import check_version
from .schema import DraftFields, DraftInfo, VersionRequest
from .service import _bump, get_draft


async def schedule_prefill(row: model.DraftTable) -> None:
    row.prefill_revision = (row.prefill_revision or 0) + 1
    row.prefill_status = "queued" if get_env().prefill_configured else "disabled"
    if row.prefill_status == "queued":
        await enqueue_job("product_drafts.prefill", {
            "draft_id": str(row.id), "revision": row.prefill_revision,
        }, available_at=utc_now() + timedelta(seconds=2))


async def retry_prefill(id: str, form: VersionRequest) -> DraftInfo:
    async with transaction():
        row = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        check_version(row.version, form.version)
        if not get_env().prefill_configured:
            raise LangException(503, DraftError.PREFILL_UNAVAILABLE)
        await schedule_prefill(row)
        _bump(row)
        await active_session().flush()
        return await get_draft(id)


async def apply_prefill(id: str, revision: int, settings_revision: int,
                        result: DraftFields) -> bool:
    async with transaction():
        settings = await model.prefill_settings_row(lock=True)
        current_settings = settings.revision if settings else 0
        row = await model.get_draft_row(id, lock=True)
        if row is None or row.prefill_revision != revision:
            return False
        if current_settings != settings_revision:
            await schedule_prefill(row)
            _bump(row)
            return False
        row.fields = merge_prefill(DraftFields.model_validate(row.fields), result,
                                   row.manual_fields or []).model_dump(mode="json")
        row.prefill_status = "ready"
        _bump(row)
        await active_session().flush()
        return True


async def _mark_failed(id: str, revision: int) -> None:
    row = await model.get_draft_row(id, lock=True)
    if row and row.prefill_revision == revision:
        row.prefill_status = "failed"
        _bump(row)
        await active_session().flush()


async def run_prefill(job: Job) -> None:
    id, revision = str(job.payload["draft_id"]), int(str(job.payload["revision"]))
    row = await model.get_draft_row(id)
    if row is None or row.prefill_revision != revision:
        return
    settings = await prefill_settings.get_settings()
    messages = await model.messages_for(id)
    if not any(item.kind == "text" and item.text and item.text.strip() for item in messages):
        await apply_prefill(id, revision, settings.revision, DraftFields())
        return
    brands = await get_brands()
    options = [{"id": brand.id, "name": brand.name} for brand in brands.list_data]
    try:
        content = build_input(messages, options, settings.supplement)
        await release_connection()
        response = await generate_prefill(BASE_PROMPT.zh, content, output_schema())
        available = await get_brands()
        result = parse_prefill(response, {brand.id for brand in available.list_data})
    except (PrefillTransportError, ValueError):
        await _mark_failed(id, revision)
        return
    await apply_prefill(id, revision, settings.revision, result)
