from datetime import timedelta

import pytest

from modules.product_drafts import rounds, service
from tests.modules.product_drafts.helpers import BASE, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_silence_never_completes_collection(db, monkeypatch):
    await rounds.receive_message(incoming())
    monkeypatch.setattr(rounds, "utc_now", lambda: BASE + timedelta(days=10))
    current = await rounds.current_collection("group-a")
    assert current.status == "collecting" and current.message_count == 1
    assert (await service.get_draft_list(20)).total_count == 0


async def test_sources_and_redelivery_do_not_change_each_other(db):
    first = await rounds.receive_message(incoming())
    duplicate = await rounds.receive_message(incoming())
    await rounds.receive_message(incoming(source="group-b"))
    assert duplicate.duplicate and first.message_id is not None
    source = await rounds.current_collection("group-a")
    other = await rounds.current_collection("group-b")
    assert source.id != other.id and source.message_count == other.message_count == 1
    await rounds.complete_collection(source.id)
    assert (await rounds.current_collection("group-b")).id == other.id
