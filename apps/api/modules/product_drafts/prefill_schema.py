from pydantic import BaseModel, ConfigDict, Field


class PrefillSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplement: str = Field(max_length=10000)
    revision: int = Field(ge=0)


class PrefillSettingsInfo(PrefillSettingsUpdate):
    configured: bool
    base_prompt: str


class PrefillPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=200000)
    supplement: str = Field(max_length=10000)
