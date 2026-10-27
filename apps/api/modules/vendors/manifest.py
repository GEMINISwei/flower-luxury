from shared.module import ModuleManifest

from .model import VendorTable
from .router import router

MODULE = ModuleManifest(name="vendors", routers=(router,), tables=(VendorTable,))
