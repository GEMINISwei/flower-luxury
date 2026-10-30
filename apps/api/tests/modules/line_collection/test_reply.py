import json

import httpx
import pytest

from modules.line_collection import transport

pytestmark = pytest.mark.asyncio


async def test_command_reply_uses_reply_token_without_leaking_errors(monkeypatch):
    def reply(request):
        assert request.url.path == "/v2/bot/message/reply"
        assert json.loads(request.content) == {"replyToken": "reply-token",
                                               "messages": [{"type": "text", "text": "已開始收集"}]}
        return httpx.Response(400, text="reply-token access-token")

    monkeypatch.setattr(transport, "LineClient", lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(reply)))
    with pytest.raises(transport.LineTransportError) as error:
        await transport.reply_message("reply-token", "已開始收集", "access-token")
    assert "token" not in str(error.value)
