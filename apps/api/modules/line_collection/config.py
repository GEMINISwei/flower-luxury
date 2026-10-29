from typing import Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings


class LineSettings(BaseSettings):
    line_channel_secret: SecretStr = SecretStr("")
    line_channel_access_token: SecretStr = SecretStr("")

    @property
    def configured(self) -> bool:
        return bool(self.line_channel_secret.get_secret_value())

    @model_validator(mode="after")
    def paired_credentials(self) -> Self:
        secret = self.line_channel_secret.get_secret_value().strip()
        token = self.line_channel_access_token.get_secret_value().strip()
        if bool(secret) != bool(token):
            raise ValueError(
                "LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN must be set together",
            )
        if secret != self.line_channel_secret.get_secret_value():
            raise ValueError("LINE credentials must not contain surrounding whitespace")
        if token != self.line_channel_access_token.get_secret_value():
            raise ValueError("LINE credentials must not contain surrounding whitespace")
        return self


def get_settings() -> LineSettings:
    return LineSettings()
