import base64
import hashlib
import hmac
import json

import pytest
from pydantic import SecretStr, ValidationError

from modules.line_collection.config import LineSettings
from modules.line_collection.rules import parse_events, verify_signature
from shared.http.errors import LangException

SECRET = "line-test-secret"


def signature(body: bytes) -> str:
    return base64.b64encode(hmac.digest(SECRET.encode(), body, hashlib.sha256)).decode()


def test_signature_uses_original_body():
    body = b'{ "events": [] }'
    verify_signature(body, signature(body), SECRET)
    for invalid in (None, "invalid", signature(b'{"events":[]}'), "非 ASCII"):
        with pytest.raises(LangException) as error:
            verify_signature(body, invalid, SECRET)
        assert error.value.status_code == 401


def test_settings_require_paired_credentials(monkeypatch):
    monkeypatch.delenv("LINE_CHANNEL_SECRET", raising=False)
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    assert not LineSettings().configured
    with pytest.raises(ValidationError):
        LineSettings(line_channel_secret=SecretStr(SECRET))
    settings = LineSettings(
        line_channel_secret=SecretStr(SECRET), line_channel_access_token=SecretStr("test-token"))
    assert settings.configured and "test-token" not in repr(settings)


@pytest.mark.parametrize("body", [b"not-json", b"null", b'{"events":{}}',
                                   b'{"events":[{"type":"message"}]}'])
def test_invalid_payload_is_rejected_before_collection(body):
    with pytest.raises(LangException) as error:
        parse_events(body)
    assert error.value.status_code == 400


def test_unknown_events_and_empty_verification_are_supported():
    assert parse_events(b'{"events":[]}').events == []
    body = {"events": [{"type": "future-event", "source": {"type": "group", "groupId": "g"},
                        "timestamp": 1793193000000, "webhookEventId": "future"}]}
    assert parse_events(json.dumps(body).encode()).events[0].type == "future-event"
