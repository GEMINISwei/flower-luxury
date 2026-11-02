from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from modules.brands.public import get_brands
from modules.vendors.public import get_vendors
from shared.db.session import active_session, release_connection
from shared.db.transaction import transaction
from shared.jobs.contracts import Job
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import model, prefill_settings
from .prefill_config import get_env
from .prefill_prompt import BASE_PROMPT
from .prefill_rules import build_input, merge_prefill, output_schema, parse_prefill
from .prefill_schema import PrefillApplication, PrefillResult
from .prefill_transport import PrefillTransportError, generate_prefill
from .schema import DraftFields, DraftQuoteInfo
from .service import _bump


async def schedule_prefill(row: model.DraftTable) -> None:
    if row.collecting or (row.prefill_revision or 0) > 0:
        return
    row.prefill_revision = 1
    row.prefill_status = "queued" if get_env().prefill_configured else "disabled"
    if row.prefill_status == "queued":
        await enqueue_job("product_drafts.prefill", {
            "draft_id": str(row.id), "revision": row.prefill_revision,
        }, available_at=utc_now() + timedelta(seconds=2), queue="ai", max_attempts=1)


async def apply_prefill(id: str, revision: int, result: PrefillResult,
                        original_quotes: list[dict]) -> PrefillApplication:
    async with transaction():
        row = await model.get_draft_row(id, lock=True)
        if (row is None or row.collecting or row.prefill_revision != revision
                or row.prefill_status != "queued"):
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


async def _mark_failed(id: str, revision: int) -> None:
    row = await model.get_draft_row(id, lock=True)
    if row and row.prefill_revision == revision and row.prefill_status == "queued":
        row.prefill_status = "failed"
        _bump(row)
        await active_session().flush()


async def run_prefill(job: Job) -> None:
    id, revision = str(job.payload["draft_id"]), int(str(job.payload["revision"]))
    row = await model.get_draft_row(id)
    if (row is None or row.collecting or row.prefill_revision != revision
            or row.prefill_status != "queued" or job.attempts != 1):
        return
    original_quotes = deepcopy(row.quotes or [])
    settings = await prefill_settings.get_settings()
    messages = await model.messages_for(id)
    if not any(item.kind == "text" and item.text and item.text.strip() for item in messages):
        await apply_prefill(id, revision, PrefillResult(), original_quotes)
        return
    brands = await get_brands()
    vendors = await get_vendors()
    options = [{"id": brand.id, "name": brand.name} for brand in brands.list_data]
    companies = [{"id": vendor.id, "name": vendor.name} for vendor in vendors.list_data]
    try:
        content = build_input(messages, options, settings.supplement, companies)
        await release_connection()
        response = await generate_prefill(BASE_PROMPT.zh, content.content,
                                          output_schema().json_schema)
        available = await get_brands()
        active_vendors = await get_vendors()
        result = parse_prefill(response.content, {brand.id for brand in available.list_data},
                               {vendor.id for vendor in active_vendors.list_data})
    except (PrefillTransportError, ValueError):
        await _mark_failed(id, revision)
        return
    await apply_prefill(id, revision, result, original_quotes)
