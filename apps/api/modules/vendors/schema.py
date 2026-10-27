from typing import Literal

from pydantic import BaseModel, computed_field

from shared.http.schema import NonEmptyText, SimpleListResponse

type VendorCountry = Literal["TW", "CN"]


class VendorCreate(BaseModel):
    name: NonEmptyText
    country: VendorCountry
    note: str | None = None


class VendorUpdate(VendorCreate):
    is_active: bool


class VendorInfo(VendorUpdate):
    id: str
    country_locked: bool

    @computed_field
    def currency(self) -> Literal["TWD", "CNY"]:
        return "TWD" if self.country == "TW" else "CNY"


class VendorList(SimpleListResponse[VendorInfo]):
    pass
