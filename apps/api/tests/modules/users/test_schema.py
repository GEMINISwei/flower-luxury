import pytest
from pydantic import TypeAdapter, ValidationError

from app.permissions import Permission
from modules.users.schema import NewPassword, UserInfo, UserMe
from shared.auth.passwords import MAX_PASSWORD_BYTES


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


# 密碼的長度上限以 bytes 計, 不是字元數: bcrypt 只看前 72 bytes, 超過的部分被靜靜忽略,
# 不擋的話兩組前 72 bytes 相同的密碼會被當成同一組。中文一個字 3 bytes, 以字元數計算
# 會讓 25 個中文字的密碼溜過去。
def test_user_create_with_too_long_password_is_rejected():
    password = TypeAdapter(NewPassword)
    assert password.validate_python("a" * MAX_PASSWORD_BYTES) == "a" * MAX_PASSWORD_BYTES

    with pytest.raises(ValidationError):
        password.validate_python("a" * (MAX_PASSWORD_BYTES + 1))
    with pytest.raises(ValidationError):
        password.validate_python("密" * 25)  # 25 個字元, 75 bytes
