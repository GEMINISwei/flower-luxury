from shared.module import ModuleManifest

from .model import ProductHistoryTable, ProductPhotoTable, ProductTable
from .router import router

MODULE = ModuleManifest(name="products", routers=(router,),
                        tables=(ProductTable, ProductHistoryTable, ProductPhotoTable))
