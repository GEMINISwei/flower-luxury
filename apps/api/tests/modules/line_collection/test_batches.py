import pytest
from sqlalchemy import select

from modules.line_collection import model, service
from modules.line_collection.schema import GroupUpdate
from modules.product_drafts import rounds
from modules.product_drafts.model import MessageTable
from modules.product_drafts.service import get_draft_list
from shared.db.session import active_session
from shared.jobs.model import JobTable
from tests.modules.line_collection.helpers import event
from tests.modules.line_collection.test_integration import enable_group, receive
from tests.modules.line_collection.test_integration import settings as settings

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_enabled_group_collects_without_start_or_end(db):
    await enable_group()
    await receive(event(second=1), event("text", second=2, message_id="description",
                                         event_id="description"))
    assert (await get_draft_list(20)).total_count == 0
    current = await rounds.current_collection("line:group-a")
    assert current.message_count == 2
    assert (await service.list_groups()).list_data[0].collecting
    completed = await rounds.complete_collection(current.id)
    assert len(completed.draft_ids) == 1


@pytest.mark.parametrize("command", ["/start", "/end"])
async def test_old_commands_have_no_control_or_reply_side_effects(db, command):
    await enable_group()
    item = event("text", text=command, second=2).model_copy(update={"replyToken": "private-token"})
    await receive(item)
    rows = list(await active_session().scalars(select(MessageTable)))
    assert len(rows) == 1 and rows[0].text == command
    assert not list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name.in_(["line_collection.reply", "line_collection.expire_reply"]))))
    assert (await rounds.current_collection("line:group-a")).status == "collecting"


async def test_disabling_group_preserves_unfinished_collection(db):
    group = await enable_group()
    await receive(event(second=1))
    before = await rounds.current_collection("line:group-a")
    await service.update_group(str(group.id), GroupUpdate(enabled=False))
    await receive(event("text", second=2))
    after = await rounds.current_collection("line:group-a")
    assert after.id == before.id and after.message_count == 1 and after.status == "collecting"
    row = await model.group_for("group-a")
    assert row is not None and not row.enabled
