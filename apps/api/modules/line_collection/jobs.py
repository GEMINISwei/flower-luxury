from modules.product_drafts.public import complete_photo, mark_photo_failed
from shared.db.session import active_session, release_connection
from shared.http.errors import LangException
from shared.jobs.contracts import Job
from shared.time import utc_now

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


async def send_reply(job: Job) -> None:
    row = await active_session().get(model.ReplyTable, str(job.payload["reply_id"]))
    if row is None:
        return
    group = await model.get_group(str(row.group_id))
    failed = row.expires_at <= utc_now()
    if not failed:
        try:
            settings = get_settings()
            await transport.reply_message(row.reply_token, row.text,
                                          settings.line_channel_access_token.get_secret_value())
        except transport.LineTransportError:
            failed = True
    if group:
        group.reply_failed = failed
    # reply token 只能使用一次, 失敗後不重試; 完成與過期皆立即清除.
    await active_session().delete(row)


async def expire_reply(job: Job) -> None:
    row = await active_session().get(model.ReplyTable, str(job.payload["reply_id"]))
    if row:
        group = await model.get_group(str(row.group_id))
        if group:
            group.reply_failed = True
        await active_session().delete(row)
