from sqlalchemy import func, select

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import grouping, model
from .collection_schema import FinalizedSnapshot, SnapshotMessage, SnapshotPhoto
from .errors import DraftError
from .prefill import schedule_prefill
from .rules import check_version
from .schema import DraftInfo, VersionRequest
from .service import _bump, get_draft


async def _snapshot(row: model.DraftTable) -> FinalizedSnapshot:
    photos = await model.photos_for(str(row.id))
    if not photos or any(photo.status not in {"stored", "ready"} or not photo.original_key
                         for photo in photos):
        raise LangException(409, DraftError.PHOTO_NOT_READY)
    messages = await model.messages_for(str(row.id))
    return FinalizedSnapshot(
        messages=[SnapshotMessage.model_validate(message.to_dict()) for message in messages],
        photos=[SnapshotPhoto(id=str(photo.id), original_key=photo.original_key or "")
                for photo in photos])


async def _finish_round(row: model.DraftTable) -> None:
    if row.collection_id is None:
        return
    await active_session().flush()
    unfinished = await active_session().scalar(select(func.count()).select_from(model.DraftTable)
        .where(model.DraftTable.collection_id == row.collection_id,
               model.DraftTable.finalized_at.is_(None)))
    if not unfinished:
        collection = await active_session().get(model.CollectionRoundTable, row.collection_id)
        if collection:
            collection.status = "finalized"


async def finalize_draft(id: str, form: VersionRequest, actor: CurrentUser) -> DraftInfo:
    async with transaction():
        row = ensure_found(await model.get_draft_row(id), DraftError.NOT_FOUND)
        await model.stream_for(row.source_key)
        row = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        if row.finalized_at is not None:
            return await get_draft(id)
        check_version(row.version, form.version)
        if row.collecting or row.processing or row.needs_confirmation:
            raise LangException(409, DraftError.NOT_READY)
        snapshot = await _snapshot(row)
        row.finalized_at, row.finalized_snapshot = utc_now(), snapshot.model_dump(mode="json")
        photos = await model.photos_for(id)
        row.processing = any(photo.status == "stored" for photo in photos)
        for photo in photos:
            if photo.status == "stored":
                await enqueue_job("product_drafts.render_photo", {"photo_id": str(photo.id),
                    "draft_id": id}, queue="images", idempotency_key=f"photo:{photo.id}")
        await schedule_prefill(row)
        _bump(row, actor)
        await _finish_round(row)
        await active_session().flush()
        return await get_draft(id)


async def split_message(id: str, form: VersionRequest, actor: CurrentUser) -> DraftInfo:
    async with transaction():
        message = ensure_found(await model.get_message_row(id), DraftError.NOT_FOUND)
        await model.stream_for(message.source_key)
        message = ensure_found(await model.get_message_row(id, lock=True), DraftError.NOT_FOUND)
        source = ensure_found(await model.get_draft_row(str(message.draft_id), lock=True),
                              DraftError.NOT_FOUND)
        check_version(source.version, form.version)
        if source.finalized_at is not None or source.processing or source.collecting:
            raise LangException(409, DraftError.NOT_READY)
        collection = await grouping._collection_for_message(message)
        created = await grouping._new_group([message], collection, actor)
        return await get_draft(str(created.id))
