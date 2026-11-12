from copy import deepcopy
from uuid import uuid4

from modules.brands.public import get_brands
from modules.vendors.public import get_vendors
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session, release_connection
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found
from shared.jobs.contracts import Job

from . import model, prefill_settings
from .collection_schema import FinalizedSnapshot
from .errors import DraftError
from .prefill_config import get_env
from .prefill_jobs import enqueue_prefill
from .prefill_prompt import BASE_PROMPT
from .prefill_rules import build_input, merge_prefill, output_schema, parse_prefill
from .prefill_schema import PrefillApplication, PrefillResult
from .prefill_transport import generate_prefill
from .rules import check_version
from .schema import DraftFields, DraftInfo, DraftQuoteInfo, VersionRequest
from .service import _bump, get_draft


async def schedule_prefill(row: model.DraftTable) -> None:
    if row.collecting or (row.prefill_revision or 0) > 0:
        return
    row.prefill_revision = 1
    row.prefill_status = "queued" if get_env().prefill_configured else "disabled"
    if row.prefill_status == "queued":
        await enqueue_prefill(row)


async def retry_prefill(id: str, form: VersionRequest, actor: CurrentUser) -> DraftInfo:
    async with transaction():
        row = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        check_version(row.version, form.version)
        if row.collecting:
            raise LangException(409, DraftError.NOT_READY)
        queued = await model.get_prefill_job(row)
        if row.prefill_status == "ready" or (queued and queued.status in {"pending", "running"}):
            return await get_draft(id)
        row.prefill_revision += 1
        row.prefill_attempts, row.prefill_status = 0, "queued"
        await enqueue_prefill(row)
        _bump(row, actor)
        await active_session().flush()
        return await get_draft(id)


async def apply_prefill(id: str, revision: int, result: PrefillResult,
                        original_quotes: list[dict]) -> PrefillApplication:
    async with transaction():
        row = await model.get_draft_row(id, lock=True)
        if (row is None or row.collecting or row.prefill_revision != revision
                or row.prefill_status not in {"queued", "unknown"}):
            return PrefillApplication(applied=False)
        row.fields = merge_prefill(DraftFields.model_validate(row.fields), result,
                                   row.manual_fields or []).model_dump(mode="json")
        # 解析期間改過詢價時, 以人工整理的整份清單為準, 包含刻意刪除.
        if (row.quotes or []) == original_quotes:
            existing = {quote["vendor_id"] for quote in row.quotes or []}
            added = [DraftQuoteInfo(id=str(uuid4()), **quote.model_dump()).model_dump(mode="json")
                     for quote in result.vendor_info if quote.vendor_id not in existing]
            row.quotes = [*(row.quotes or []), *added]
        row.prefill_status = "ready"
        _bump(row)
        await active_session().flush()
        return PrefillApplication(applied=True)


async def run_prefill(job: Job) -> None:
    id, revision = str(job.payload["draft_id"]), int(str(job.payload["revision"]))
    row = await model.get_draft_row(id)
    if (row is None or row.collecting or row.prefill_revision != revision
            or row.prefill_status not in {"queued", "unknown"}):
        return
    original_quotes = deepcopy(row.quotes or [])
    settings = await prefill_settings.get_settings()
    snapshot = FinalizedSnapshot.model_validate(row.finalized_snapshot) \
        if row.finalized_snapshot is not None else None
    messages = snapshot.messages if snapshot else await model.messages_for(id)
    if not any(item.kind == "text" and item.text and item.text.strip() for item in messages):
        await apply_prefill(id, revision, PrefillResult(), original_quotes)
        return
    brands = await get_brands()
    vendors = await get_vendors()
    options = [{"id": brand.id, "name": brand.name} for brand in brands.list_data]
    companies = [{"id": vendor.id, "name": vendor.name} for vendor in vendors.list_data]
    content = build_input(messages, options, settings.supplement, companies)
    await release_connection()
    response = await generate_prefill(BASE_PROMPT.zh, content.content, output_schema().json_schema)
    available = await get_brands()
    active_vendors = await get_vendors()
    result = parse_prefill(response.content, {brand.id for brand in available.list_data},
                           {vendor.id for vendor in active_vendors.list_data})
    await apply_prefill(id, revision, result, original_quotes)
