from shared.module import ModuleManifest

from .model import BrandTable
from .router import router

MODULE = ModuleManifest(name="brands", routers=(router,), tables=(BrandTable,))
