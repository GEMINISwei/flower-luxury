import pytest
from pydantic import ValidationError

from modules.product_drafts.rules import decide_collection
from modules.product_drafts.schema import DraftFields, DraftUpdate, IncomingMessage, PhotoOrder
from tests.modules.product_drafts.helpers import BASE, ID


@pytest.mark.parametrize("kind,current,text,late,assign,start", [
    ("image", False, False, False, True, True),
    ("image", True, False, False, True, False),
    ("image", True, True, False, True, True),
    ("text", True, False, False, True, False),
    ("text", True, True, False, True, False),
    ("text", False, False, False, False, False),
    ("image", True, True, True, False, False),
    ("text", True, True, True, False, False),
])
def test_collection_decisions(kind, current, text, late, assign, start):
    decision = decide_collection(kind, has_current=current, has_text=text, is_late=late)
    assert decision.assign == assign and decision.start_new == start


@pytest.mark.parametrize("data", [
    {"version": 0, "fields": {}},
    {"version": 1, "fields": {"cost_price": -1}},
    {"version": 1, "fields": {"cost_price": True}},
    {"version": 1, "fields": {"year": 10000}},
    {"version": 1, "fields": {"brand_id": "bad"}},
    {"version": 1, "fields": {"status": "sold"}},
])
def test_draft_schemas_reject_invalid_mutations(data):
    with pytest.raises(ValidationError):
        DraftUpdate.model_validate(data)


def test_incomplete_fields_are_allowed_but_duplicate_photo_ids_are_not():
    assert DraftFields().name is None
    assert DraftFields(name="", cost_price=0).name == ""
    with pytest.raises(ValidationError):
        PhotoOrder(version=1, photo_ids=[ID, ID])


@pytest.mark.parametrize("kind,text", [("text", None), ("image", "unexpected")])
def test_incoming_message_requires_matching_content(kind, text):
    with pytest.raises(ValidationError):
        IncomingMessage(source_key="group", external_id="m", kind=kind,
                        text=text, occurred_at=BASE)
