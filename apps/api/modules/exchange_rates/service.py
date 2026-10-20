from shared.auth.contracts import CurrentUser

from .model import ExchangeRateTable
from .schema import ExchangeRateSettings, ExchangeRateUpdate


async def get_settings() -> ExchangeRateSettings:
    data = await ExchangeRateTable.read_settings()
    return ExchangeRateSettings.model_validate(data) if data else ExchangeRateSettings()


async def update_settings(
    form_data: ExchangeRateUpdate, actor: CurrentUser,
) -> ExchangeRateSettings:
    await ExchangeRateTable.write_rate(form_data.rate, actor)
    return await get_settings()
