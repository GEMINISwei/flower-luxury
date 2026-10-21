from pydantic import BaseModel

from shared.http.schema import NonEmptyText, SimpleListResponse


class BrandCreate(BaseModel):
    name: NonEmptyText


class BrandUpdate(BrandCreate):
    is_active: bool


class BrandInfo(BrandUpdate):
    id: str
    in_use: bool


class BrandList(SimpleListResponse[BrandInfo]):
    pass
