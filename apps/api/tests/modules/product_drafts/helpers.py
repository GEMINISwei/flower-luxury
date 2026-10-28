import uuid
from datetime import datetime
from io import BytesIO

from PIL import Image

from modules.product_drafts.schema import DraftFields, DraftInfo, IncomingMessage
from shared.auth.contracts import CurrentUser

ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}
ID = "11111111-1111-4111-8111-111111111111"
BASE = datetime(2026, 10, 28, 12)


def incoming(kind="image", *, source="group-a", text=None, second=0, external_id=None):
    return IncomingMessage(source_key=source, external_id=external_id or uuid.uuid4().hex,
                           kind=kind, text=text, occurred_at=BASE.replace(second=second),
                           sender_id="sender", sender_name="供應商")


def image_bytes():
    output = BytesIO()
    Image.new("RGB", (8, 4), "red").save(output, format="PNG")
    return output.getvalue()


def info(version=1):
    return DraftInfo(id=ID, source_key="group-a", version=version, fields=DraftFields(),
                     main_photo_id=None, collecting=True, created_at=BASE, updated_at=None,
                     messages=[], photos=[])
