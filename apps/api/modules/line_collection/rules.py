import base64
import hashlib
import hmac
import json

from pydantic import ValidationError

from shared.http.errors import LangException

from .errors import LineError
from .schema import Fingerprint, WebhookBody

MAX_WEBHOOK_BYTES = 1024 * 1024


def verify_signature(body: bytes, signature: str | None, secret: str) -> None:
    expected = base64.b64encode(hmac.digest(secret.encode(), body, hashlib.sha256))
    supplied = signature.encode("utf-8") if signature else b""
    if not secret or not hmac.compare_digest(expected, supplied):
        raise LangException(401, LineError.SIGNATURE)


def parse_events(body: bytes) -> WebhookBody:
    if len(body) > MAX_WEBHOOK_BYTES:
        raise LangException(413, LineError.TOO_LARGE)
    try:
        return WebhookBody.model_validate_json(body)
    except (ValidationError, ValueError, OverflowError) as error:
        raise LangException(400, LineError.PAYLOAD) from error


def fingerprint(group_id: str, external_id: str) -> Fingerprint:
    return Fingerprint(value=hashlib.sha256(
        json.dumps([group_id, external_id]).encode(),
    ).hexdigest())
