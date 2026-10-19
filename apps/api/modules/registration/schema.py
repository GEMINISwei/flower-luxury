from typing import Annotated

from pydantic import BaseModel, StringConstraints

from modules.users.public import SuperAdminCreate


class SignupRequest(SuperAdminCreate):
    registration_key: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class RegistrationSettingsUpdate(BaseModel):
    registration_key: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class RegistrationSettings(BaseModel):
    configured: bool
