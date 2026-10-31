from pydantic import SecretStr
from pydantic_settings import BaseSettings


class PrefillEnv(BaseSettings):
    gemini_api_key: SecretStr = SecretStr("")

    @property
    def prefill_configured(self) -> bool:
        return bool(self.gemini_api_key.get_secret_value().strip())


def get_env() -> PrefillEnv:
    return PrefillEnv()
