from pydantic import BaseModel

from shared.http.schema import NonEmptyText, SimpleListResponse


class BrandCreate(BaseModel):
    name: NonEmptyText


class BrandUpdate(BrandCreate):
    is_active: bool


class BrandInfo(BrandUpdate):
    id: str


class BrandList(SimpleListResponse[BrandInfo]):
    pass
