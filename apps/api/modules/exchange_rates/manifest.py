from shared.module import ModuleManifest

from .model import ExchangeRateTable
from .router import router

MODULE = ModuleManifest(name="exchange_rates", routers=(router,), tables=(ExchangeRateTable,))
