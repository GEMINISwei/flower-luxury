from shared.module import ModuleManifest

from .model import RegistrationTable
from .router import router

MODULE = ModuleManifest(
    name="registration", routers=(router,), tables=(RegistrationTable,),
)
