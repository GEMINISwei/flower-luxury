from typing import Any

import httpx

from .prefill_config import get_env

MODEL = "gemini-3.5-flash-lite"


class PrefillTransportError(Exception):
    pass


async def generate_prefill(system_prompt: str, input_text: str,
                           schema: dict[str, Any]) -> str:
    env = get_env()
    if not env.prefill_configured:
        raise PrefillTransportError()
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                headers={"x-goog-api-key": env.gemini_api_key.get_secret_value()},
                json={"systemInstruction": {"parts": [{"text": system_prompt}]},
                      "contents": [{"role": "user", "parts": [{"text": input_text}]}],
                      "generationConfig": {"responseMimeType": "application/json",
                                           "responseJsonSchema": schema,
                                           "maxOutputTokens": 4096}},
            )
            response.raise_for_status()
            candidate = response.json()["candidates"][0]
            if candidate.get("finishReason") != "STOP":
                raise PrefillTransportError()
            content = "".join(part.get("text", "") for part in candidate["content"]["parts"]
                              if not part.get("thought"))
            if not content or len(content) > 50000:
                raise PrefillTransportError()
            return content
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
        raise PrefillTransportError() from error
