import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import ForeignKey, Index, String, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import active_session
from shared.db.table import BaseTable, PagedResult, parse_uuid
from shared.time import utc_now

from .schema import DownloadTarget, SourceInfo, SourceList


class GroupTable(BaseTable):
    __tablename__ = "line_groups"
    group_id: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str | None]
    enabled: Mapped[bool] = mapped_column(default=False)
    joined: Mapped[bool] = mapped_column(default=True)
    last_membership_at: Mapped[datetime | None]
    collect_from: Mapped[datetime | None]
    review_product_id: Mapped[str | None]
    reply_failed: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (Index("ix_line_groups_created_at_id", "created_at", "id"),)


class EventReceiptTable(BaseTable):
    __tablename__ = "line_event_receipts"
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(index=True)


class MessageLinkTable(BaseTable):
    __tablename__ = "line_message_links"
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("line_groups.id", ondelete="CASCADE"))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    external_id: Mapped[str | None] = mapped_column(String(200))
    # 暫存刪除或審核後僅留下防重送摘要, 不保留傳送者或訊息原文.
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_draft_messages.id", ondelete="SET NULL"),
    )
    draft_id: Mapped[str | None]
    revoked: Mapped[bool] = mapped_column(default=False)
    expires_at: Mapped[datetime] = mapped_column(index=True)


async def group_for(group_id: str) -> GroupTable | None:
    return await active_session().scalar(select(GroupTable).where(
        GroupTable.group_id == group_id,
    ).with_for_update().execution_options(populate_existing=True))


async def discover_group(group_id: str) -> tuple[GroupTable, bool]:
    created = await active_session().scalar(insert(GroupTable).values(group_id=group_id)
        .on_conflict_do_nothing(index_elements=[GroupTable.group_id]).returning(GroupTable.id))
    group = await group_for(group_id)
    if group is None:
        raise RuntimeError("group discovery failed")
    return group, created is not None


async def get_group(id: str, *, lock: bool = False) -> GroupTable | None:
    statement = select(GroupTable).where(GroupTable.id == parse_uuid(id))
    if lock:
        statement = statement.with_for_update()
    return await active_session().scalar(statement.execution_options(populate_existing=True))


async def group_page(limit: int, cursor: str | None,
                     direction: Literal["next", "prev"]) -> PagedResult:
    return await GroupTable.get_page(limit=limit, cursor=cursor, direction=direction)


async def source_list() -> SourceList:
    rows = await active_session().execute(select(GroupTable.group_id, GroupTable.name)
                                          .order_by(GroupTable.created_at, GroupTable.id))
    return SourceList(list_data=[SourceInfo(source_key=f"line:{id}", name=name)
                                 for id, name in rows])


async def receipt_exists(digest: str) -> bool:
    return await active_session().scalar(select(EventReceiptTable.id).where(
        EventReceiptTable.fingerprint == digest,
    )) is not None


async def message_link(digest: str) -> MessageLinkTable | None:
    return await active_session().scalar(select(MessageLinkTable).where(
        MessageLinkTable.fingerprint == digest,
    ).execution_options(populate_existing=True))


async def download_target(id: str) -> DownloadTarget | None:
    link = await active_session().get(MessageLinkTable, parse_uuid(id))
    if link is None:
        return None
    if link.revoked or not link.message_id or not link.external_id:
        link.external_id = None
        await active_session().flush()
        return None
    return DownloadTarget(message_id=str(link.message_id), external_id=link.external_id)


async def save_group_name(id: str, name: str) -> None:
    group = await get_group(id, lock=True)
    if group:
        group.name = name
        await active_session().flush()


async def expire_row(id: str, kind: str) -> None:
    table = EventReceiptTable if kind == "event" else MessageLinkTable
    await active_session().execute(delete(table).where(
        table.id == parse_uuid(id), table.expires_at <= utc_now(),
    ))


async def clear_download_id(id: str) -> None:
    link = await active_session().get(MessageLinkTable, parse_uuid(id))
    if link:
        link.external_id = None
        await active_session().flush()


class ReplyTable(BaseTable):
    __tablename__ = "line_command_replies"
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("line_groups.id", ondelete="CASCADE"))
    reply_token: Mapped[str] = mapped_column(String(200))
    text: Mapped[str]
    expires_at: Mapped[datetime]
