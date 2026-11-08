import pytest
from pydantic import ValidationError

from app.permissions import Permission
from modules.roles.schema import RoleCreate, RoleInfo, RoleUpdate


def test_role_response_drops_removed_permissions():
    result = RoleInfo.model_validate(
        {
            "id": "role-1",
            "name": "角色",
            "permissions": [Permission.ALL.value, "removed:read"],
            "is_disabled": False,
        }
    )

    assert result.permissions == [Permission.ALL]
    assert result.model_dump(mode="json")["permissions"] == [Permission.ALL.value]


@pytest.mark.parametrize("model", [RoleCreate, RoleUpdate])
def test_role_write_still_rejects_unknown_permissions(model):
    with pytest.raises(ValidationError):
        model.model_validate(
            {"name": "角色", "permissions": ["removed:read"], "is_disabled": False}
        )
