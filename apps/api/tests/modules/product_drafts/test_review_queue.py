import pytest

from modules.product_drafts import collection, service
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
