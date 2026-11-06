import pytest

from modules.product_drafts import collection, service
from shared.http.errors import LangException
from tests.modules.product_drafts.helpers import incoming

pytestmark = pytest.mark.asyncio


@pytest.mark.integration
async def test_draft_list_is_oldest_first_across_pages_and_filter(db):
    expected = []
    for second in (5, 1, 3):
        result = await collection.ingest_message(incoming(source=f"group-{second}", second=second))
        assert result.draft_id
        expected.append((second, result.draft_id))
    ids = []
    cursor = None
    for _ in range(3):
        page = await service.get_draft_list(1, cursor=cursor)
        ids.append(page.list_data[0].id)
        cursor = page.next_cursor
    assert ids == [id for _, id in sorted(expected)]
    page = await service.get_draft_list(20, source_key="group-3")
    assert [item.id for item in page.list_data] == [expected[2][1]]


@pytest.mark.integration
@pytest.mark.parametrize("source_key", [None, "group-a"])
async def test_list_position_matches_page_containing_draft(db, source_key):
    for index in range(5):
        for source in ("group-a", "group-b"):
            await collection.ingest_message(incoming(source=source, second=index * 2))
            await collection.ingest_message(
                incoming("text", source=source, second=index * 2 + 1, text="說明"))
    cursor, seq = None, 1
    while True:
        page = await service.get_draft_list(2, cursor=cursor, source_key=source_key)
        for item in page.list_data:
            position = await service.get_list_position(item.id, 2, source_key)
            assert (position.cursor, position.seq) == (cursor, seq)
        if not page.has_next:
            break
        cursor, seq = page.next_cursor, seq + 1
    assert seq > 1


@pytest.mark.integration
async def test_list_position_of_missing_draft_is_not_found(db):
    with pytest.raises(LangException):
        await service.get_list_position("00000000-0000-4000-8000-000000000000", 20)
