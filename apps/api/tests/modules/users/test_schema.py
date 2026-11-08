import pytest

from app.permissions import Permission
from modules.users.schema import UserInfo, UserMe


@pytest.mark.parametrize("model", [UserInfo, UserMe])
def test_user_response_drops_removed_permissions(model):
    result = model.model_validate(
        {
            "id": "user-1",
            "username": "staff",
            "nickname": "員工",
            "role_ids": [],
            "permissions": [Permission.ALL.value, "removed:read"],
            "is_disabled": False,
        }
    )

    assert result.permissions == [Permission.ALL]
    assert result.model_dump(mode="json")["permissions"] == [Permission.ALL.value]
