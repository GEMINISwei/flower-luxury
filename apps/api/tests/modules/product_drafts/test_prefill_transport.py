import httpx
import pytest

from modules.product_drafts import prefill_transport

pytestmark = pytest.mark.asyncio


async def test_gemini_requests_json_schema_and_rejects_blocked_responses(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    original_client = httpx.AsyncClient
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": '{"name":null}'}]}}]})

    monkeypatch.setattr(prefill_transport.httpx, "AsyncClient", lambda **kwargs:
                        original_client(transport=httpx.MockTransport(respond), **kwargs))
    result = await prefill_transport.generate_prefill("base", "input", {"type": "object"})
    assert result == '{"name":null}'
    assert calls[0].headers["x-goog-api-key"] == "test-key"
    assert "gemini-3.5-flash-lite:generateContent" in str(calls[0].url)
    import json

    body = json.loads(calls[0].content)
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseJsonSchema"] == {"type": "object"}
    assert body["systemInstruction"]["parts"][0]["text"] == "base"


@pytest.mark.parametrize("body", [
    {"candidates": []}, {"candidates": [{"finishReason": "SAFETY"}]},
    {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{}"}]}}]},
])
async def test_gemini_rejects_incomplete_results(monkeypatch, body):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    original_client = httpx.AsyncClient
    monkeypatch.setattr(prefill_transport.httpx, "AsyncClient", lambda **kwargs:
        original_client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body)),
                        **kwargs))
    with pytest.raises(prefill_transport.PrefillTransportError):
        await prefill_transport.generate_prefill("base", "input", {"type": "object"})
