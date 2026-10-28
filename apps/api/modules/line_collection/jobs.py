from modules.product_drafts.public import complete_photo, mark_photo_failed
from shared.db.session import release_connection
from shared.http.errors import LangException
from shared.jobs.contracts import Job

from . import model, transport
from .config import get_settings


async def download_photo(job: Job) -> None:
    target = await model.download_target(str(job.payload["link_id"]))
    if target is None:
        return
    await release_connection()
    try:
        settings = get_settings()
        if not settings.configured:
            raise transport.LineTransportError()
        content = await transport.download_image(
            target.external_id, settings.line_channel_access_token.get_secret_value(),
        )
        await complete_photo(target.message_id, content.content, None)
    except (transport.LineTransportError, LangException):
        if job.attempts < 3:
            raise
        await mark_photo_failed(target.message_id)
    await model.clear_download_id(str(job.payload["link_id"]))


async def refresh_group_name(job: Job) -> None:
    group = await model.get_group(str(job.payload["group_id"]))
    if group is None:
        return
    id, group_id = str(group.id), group.group_id
    await release_connection()
    try:
        settings = get_settings()
        name = await transport.group_name(
            group_id, settings.line_channel_access_token.get_secret_value(),
        )
    except transport.LineTransportError:
        if job.attempts < 3:
            raise
        return
    await model.save_group_name(id, name.name)


async def expire_receipt(job: Job) -> None:
    await model.expire_row(str(job.payload["id"]), str(job.payload["kind"]))
