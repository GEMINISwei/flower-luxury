import pytest
from pydantic import ValidationError

from modules.products.rules import ensure_transition
from modules.products.schema import StatusChange, StatusReturn
from shared.http.errors import LangException


@pytest.mark.parametrize("source,target,returning,allowed", [
    ("not_acquired", "sold", False, False), ("sold", "not_acquired", False, False),
    ("sold", "not_acquired", True, True), ("not_acquired", "not_acquired", True, False),
    ("sold", "sold", True, False), ("not_acquired", "in_stock", False, False),
    ("sold", "in_stock", True, False), ("in_stock", "not_acquired", True, False),
])
def test_status_transitions_follow_workflow(source, target, returning, allowed):
    if allowed:
        ensure_transition(source, target, returning=returning)
    else:
        with pytest.raises(LangException) as error:
            ensure_transition(source, target, returning=returning)
        assert error.value.status_code == 409


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_return_requires_reason(reason):
    with pytest.raises(ValidationError):
        StatusReturn(to_status="not_acquired", reason=reason)
    assert StatusChange(to_status="sold").reason is None


@pytest.mark.parametrize("model", [StatusChange, StatusReturn])
def test_status_payload_rejects_removed_in_stock(model):
    with pytest.raises(ValidationError):
        model(to_status="in_stock", reason="legacy")
