from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from modules.product_drafts import issues, messages, model
from modules.product_drafts.schema import ResolveIssue
from shared.http.errors import LangException
from tests.modules.product_drafts.helpers import ACTOR, BASE, ID

pytestmark = pytest.mark.asyncio


@pytest.fixture
def context(monkeypatch):
    event = SimpleNamespace(id=ID, source_key="group-a", status="issue", message_id=uuid4())
    target = SimpleNamespace(collecting=False, processing=False)
    session = SimpleNamespace(delete=AsyncMock(), flush=AsyncMock())

    @asynccontextmanager
    async def transaction():
        yield session

    monkeypatch.setattr(issues, "transaction", transaction)
    monkeypatch.setattr(issues, "active_session", lambda: session)
    monkeypatch.setattr(model, "get_buffered_event", AsyncMock(return_value=event))
    monkeypatch.setattr(model, "get_draft_row", AsyncMock(return_value=target))
    monkeypatch.setattr(model, "refresh_source_confirmation", AsyncMock())
    move = AsyncMock()
    discard = AsyncMock()
    monkeypatch.setattr(messages, "move_message", move)
    monkeypatch.setattr(messages, "discard_legacy_message", discard)
    return SimpleNamespace(event=event, target=target, session=session, move=move, discard=discard)


@pytest.mark.parametrize("condition,code", [
    ("pending", 409), ("no_message", 422), ("no_target", 422),
    ("collecting", 409), ("processing", 409), ("finalized", 409),
])
async def test_resolve_issue_rejects_unfinished_or_invalid_targets(context, condition, code):
    if condition == "pending":
        context.event.status = "pending"
    elif condition == "no_message":
        context.event.message_id = None
    elif condition in {"collecting", "processing"}:
        setattr(context.target, condition, True)
    elif condition == "finalized":
        context.target.finalized_at = BASE
    form = ResolveIssue(action="attach", target_draft_id=None if condition == "no_target" else ID,
                        target_version=5)
    with pytest.raises(LangException) as error:
        await issues.resolve_issue(ID, form, ACTOR)
    assert error.value.status_code == code
    context.move.assert_not_awaited()
    context.discard.assert_not_awaited()


async def test_resolve_issue_passes_target_version_and_operator_to_attachment(context):
    result = await issues.resolve_issue(ID, ResolveIssue(action="attach", target_draft_id=ID,
                                                        target_version=5), ACTOR)
    assert result.id == ID
    args = context.move.call_args.args
    assert args[0] == str(context.event.message_id)
    assert args[1].target_draft_id == ID and args[1].target_version == 5 and args[2] == ACTOR


@pytest.mark.parametrize("command", [False, True])
async def test_resolve_issue_discard_cleans_message_or_releases_command(context, command):
    if command:
        context.event.message_id = None
    result = await issues.resolve_issue(ID, ResolveIssue(action="discard"), ACTOR)
    assert result.id == ID
    if command:
        context.session.delete.assert_awaited_once_with(context.event)
        assert isinstance(model.refresh_source_confirmation, AsyncMock)
        model.refresh_source_confirmation.assert_awaited_once_with("group-a")
    else:
        context.discard.assert_awaited_once_with(str(context.event.message_id))


async def test_issue_listing_preserves_text_image_and_control_information(context, monkeypatch):
    text_id, image_id = uuid4(), uuid4()
    rows = [{"id": uuid4(), "source_key": "group-a", "occurred_at": BASE,
             "message_id": message_id, "kind": kind}
            for message_id, kind in [(text_id, "message"), (image_id, "message"), (None, "end")]]
    page = {"list_data": rows, "total_count": 3, "has_next": False, "has_previous": False}
    monkeypatch.setattr(model, "buffered_issue_page", AsyncMock(return_value=page))
    stored = {str(text_id): SimpleNamespace(id=text_id, kind="text", text="原文\n完整保留"),
              str(image_id): SimpleNamespace(id=image_id, kind="image", text=None)}
    monkeypatch.setattr(model, "get_message_row", AsyncMock(side_effect=stored.get))
    photo = model.PhotoTable(id=uuid4(), message_id=image_id, status="ready", sort_order=1)
    monkeypatch.setattr(model, "photo_for_message", AsyncMock(side_effect=lambda id:
        photo if id == str(image_id) else None))
    result = await issues.get_issues(20, source_key="group-a")
    assert result.list_data[0].text == "原文\n完整保留"
    assert result.list_data[1].photo is not None and result.list_data[1].photo.url
    assert result.list_data[2].kind == "end" and result.list_data[2].text is None


async def test_issue_listing_skips_message_withdrawn_during_read(context, monkeypatch):
    page = {"list_data": [{"id": uuid4(), "source_key": "group-a", "occurred_at": BASE,
                           "message_id": uuid4(), "kind": "message"}],
            "total_count": 1, "has_next": False, "has_previous": False}
    monkeypatch.setattr(model, "buffered_issue_page", AsyncMock(return_value=page))
    monkeypatch.setattr(model, "get_message_row", AsyncMock(return_value=None))
    result = await issues.get_issues(20, source_key="group-a")
    assert result.list_data == []
