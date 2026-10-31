from pydantic import BaseModel

from shared.http.schema import NonEmptyText, SimpleListResponse


class VendorCreate(BaseModel):
    name: NonEmptyText
    note: str | None = None


class VendorUpdate(VendorCreate):
    is_active: bool


class VendorInfo(VendorUpdate):
    id: str
    has_quotes: bool


class VendorList(SimpleListResponse[VendorInfo]):
    pass
