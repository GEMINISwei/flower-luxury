from datetime import timedelta
from typing import Literal

from modules.product_drafts.public import (
    IncomingMessage,
    finish_collection,
    get_collection_state,
    withdraw_message,
)
from modules.product_drafts.public import receive_message as ingest_message
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
from .schema import GroupInfo, GroupList, GroupUpdate, LineEvent, SourceList, WebhookResult


async def list_sources() -> SourceList:
    listing = await model.source_list()
    for item in listing.list_data:
        state = await get_collection_state(item.source_key)
        item.current_round_id, item.received_count = state.current_round_id, state.received_count
    return listing


async def list_groups(limit: int = 20, cursor: str | None = None,
                      direction: Literal["next", "prev"] = "next") -> GroupList:
    page = await model.group_page(limit, cursor, direction)
    for row in page["list_data"]:
        row.update((await get_collection_state(f"line:{row['group_id']}")).model_dump())
    return GroupList.model_validate(page)


async def update_group(id: str, form: GroupUpdate) -> GroupInfo:
    async with transaction():
        row = ensure_found(await model.get_group(id, lock=True), LineError.NOT_FOUND)
        if form.enabled and not row.joined:
            raise LangException(409, LineError.LEFT)
        if form.enabled and not row.enabled:
            row.collect_from = utc_now()
        row.enabled = form.enabled
        await active_session().flush()
        return await _group_info(row)


async def _group_info(row: model.GroupTable) -> GroupInfo:
    state = await get_collection_state(f"line:{row.group_id}")
    return GroupInfo.model_validate({**row.to_dict(), **state.model_dump()})


async def stop_group(id: str) -> GroupInfo:
    async with transaction():
        row = ensure_found(await model.get_group(id, lock=True), LineError.NOT_FOUND)
        await finish_collection(f"line:{row.group_id}", utc_now())
        return await _group_info(row)


async def _remember(group: model.GroupTable, event: LineEvent) -> bool:
    digest = fingerprint(group.group_id, event.webhookEventId).value
    if await model.receipt_exists(digest):
        return False
    row = model.EventReceiptTable(fingerprint=digest, expires_at=utc_now() + timedelta(days=30))
    active_session().add(row)
    await active_session().flush()
    await enqueue_job("line_collection.expire", {"id": str(row.id), "kind": "event"},
                      available_at=row.expires_at, queue="maintenance")
    return True


async def _new_link(group: model.GroupTable, external_id: str) -> model.MessageLinkTable:
    row = model.MessageLinkTable(group_id=group.id,
                                 fingerprint=fingerprint(group.group_id, external_id).value,
                                 expires_at=utc_now() + timedelta(days=30))
    active_session().add(row)
    await active_session().flush()
    await enqueue_job("line_collection.expire", {"id": str(row.id), "kind": "link"},
                      available_at=row.expires_at, queue="maintenance")
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
    if not result.message_id:
        return False
    link = await _new_link(group, external_id)
    link.message_id = parse_uuid(result.message_id or "")
    link.draft_id = result.draft_id
    # 外部 message ID 只在待下載期間保存, 工作完成或暫存移除後不再需要.
    if kind == "image" and result.message_id:
        link.external_id = external_id
        await enqueue_job("line_collection.download", {"link_id": str(link.id)}, queue="downloads")
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
        # 固定鎖定順序避免跨群組互鎖, 同一封 Webhook 依原始傳送時間處理.
        ordered = sorted(events, key=lambda item: (item.source.get("groupId", ""), item.timestamp))
        for event in ordered:
            accepted += await _handle(event)
    return WebhookResult(accepted=accepted)
