from datetime import timedelta
from typing import Literal

from modules.product_drafts.public import IncomingMessage, ingest_message, withdraw_message
from shared.db.session import active_session
from shared.db.table import parse_uuid
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import model
from .config import LineSettings
from .errors import LineError
from .rules import fingerprint, parse_events, verify_signature
from .schema import GroupInfo, GroupList, GroupUpdate, LineEvent, WebhookResult


async def list_groups(limit: int = 20, cursor: str | None = None,
                      direction: Literal["next", "prev"] = "next") -> GroupList:
    return GroupList.model_validate(await model.group_page(limit, cursor, direction))


async def update_group(id: str, form: GroupUpdate) -> GroupInfo:
    async with transaction():
        row = ensure_found(await model.get_group(id, lock=True), LineError.NOT_FOUND)
        if form.enabled and not row.joined:
            raise LangException(409, LineError.LEFT)
        if form.enabled and not row.enabled:
            row.collect_from = utc_now()
        row.enabled = form.enabled
        await active_session().flush()
        return GroupInfo.model_validate(row.to_dict())


async def _remember(group: model.GroupTable, event: LineEvent) -> bool:
    digest = fingerprint(group.group_id, event.webhookEventId).value
    if await model.receipt_exists(digest):
        return False
    row = model.EventReceiptTable(fingerprint=digest, expires_at=utc_now() + timedelta(days=30))
    active_session().add(row)
    await active_session().flush()
    await enqueue_job("line_collection.expire", {"id": str(row.id), "kind": "event"},
                      available_at=row.expires_at)
    return True


async def _new_link(group: model.GroupTable, external_id: str) -> model.MessageLinkTable:
    row = model.MessageLinkTable(group_id=group.id,
                                 fingerprint=fingerprint(group.group_id, external_id).value,
                                 expires_at=utc_now() + timedelta(days=30))
    active_session().add(row)
    await active_session().flush()
    await enqueue_job("line_collection.expire", {"id": str(row.id), "kind": "link"},
                      available_at=row.expires_at)
    return row


async def _collect(group: model.GroupTable, event: LineEvent) -> bool:
    message = event.message or {}
    kind = message.get("type")
    if (not group.enabled or not group.joined or kind not in {"text", "image"}
            or not group.collect_from or event.occurred_at < group.collect_from):
        return False
    if not await _remember(group, event):
        return False
    external_id = str(message["id"])
    if await model.message_link(fingerprint(group.group_id, external_id).value):
        return False
    result = await ingest_message(IncomingMessage(
        source_key=f"line:{group.group_id}", external_id=external_id, kind=kind,
        text=str(message["text"]) if kind == "text" else None,
        sender_id=event.source.get("userId"), occurred_at=event.occurred_at,
    ))
    link = await _new_link(group, external_id)
    link.message_id = parse_uuid(result.message_id or "")
    link.draft_id = result.draft_id
    # 外部 message ID 只在待下載期間保存, 工作完成或暫存移除後不再需要.
    if kind == "image" and result.message_id:
        link.external_id = external_id
        await enqueue_job("line_collection.download", {"link_id": str(link.id)})
    return not result.duplicate


async def _unsend(group: model.GroupTable, event: LineEvent) -> None:
    external_id = (event.unsend or {})["messageId"]
    link = await model.message_link(fingerprint(group.group_id, external_id).value)
    if link is None:
        link = await _new_link(group, external_id)
    result = await withdraw_message(f"line:{group.group_id}", external_id, link.draft_id)
    link.revoked = True
    link.external_id = None
    if result.product_id:
        group.review_product_id = result.product_id


async def _handle(event: LineEvent) -> bool:
    group_id = event.source.get("groupId")
    if event.mode != "active" or event.source.get("type") != "group" or not group_id:
        return False
    group, created = await model.discover_group(group_id)
    refresh_name = created
    if event.type in {"join", "leave"}:
        if group.last_membership_at is None or event.occurred_at > group.last_membership_at:
            group.last_membership_at = event.occurred_at
            group.joined = event.type == "join"
            refresh_name = refresh_name or group.joined
            if not group.joined:
                group.enabled = False
    elif event.type == "unsend":
        # 停用只阻止新收件, 已收內容的撤回仍然必須處理.
        await _unsend(group, event)
    elif event.type == "message":
        if refresh_name:
            await enqueue_job("line_collection.group_name", {"group_id": str(group.id)})
        return await _collect(group, event)
    if refresh_name:
        await enqueue_job("line_collection.group_name", {"group_id": str(group.id)})
    return False


async def receive_webhook(body: bytes, signature: str | None,
                          settings: LineSettings) -> WebhookResult:
    if not settings.configured:
        raise LangException(503, LineError.DISABLED)
    verify_signature(body, signature, settings.line_channel_secret.get_secret_value())
    events = parse_events(body).events
    accepted = 0
    async with transaction():
        # 固定鎖定順序避免兩個多群組批次互鎖, 各群組內保留 LINE 原始事件順序.
        for event in sorted(events, key=lambda item: item.source.get("groupId", "")):
            accepted += await _handle(event)
    return WebhookResult(accepted=accepted)
