from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import collection, photos
from shared.http.errors import LangException
from shared.jobs import processes
from tests.modules.product_drafts.helpers import image_bytes, incoming
from tests.modules.product_drafts.test_services import state as state

pytestmark = pytest.mark.asyncio


async def test_photo_completion_uses_terminable_process(state, monkeypatch):
    async def execute(function, *args, **kwargs):
        return function(*args)

    run = AsyncMock(side_effect=execute)
    monkeypatch.setattr(photos, "run_process", run)
    message = await collection.ingest_message(incoming())
    result = await photos.complete_photo(message.message_id, image_bytes(), "original.png")
    assert result.accepted and result.photo is not None and result.photo.status == "ready"
    assert run.await_count == 1


async def test_child_failure_does_not_expose_image_data(state, monkeypatch):
    monkeypatch.setattr(photos, "run_process",
                        AsyncMock(side_effect=processes.ProcessExecutionError("ValueError")))
    message = await collection.ingest_message(incoming())
    with pytest.raises(LangException) as error:
        await photos.complete_photo(message.message_id, image_bytes(), "original.png")
    assert error.value.status_code == 422
