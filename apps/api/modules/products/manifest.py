from shared.module import ModuleManifest

from .model import (
    ProductHistoryTable,
    ProductPhotoTable,
    ProductQuoteTable,
    ProductSaleTable,
    ProductTable,
)
from .quote_router import router as quote_router
from .router import router
from .sale_router import router as sale_router

MODULE = ModuleManifest(
    name="products", routers=(router, quote_router, sale_router),
    tables=(ProductTable, ProductHistoryTable, ProductPhotoTable,
            ProductQuoteTable, ProductSaleTable),
)
