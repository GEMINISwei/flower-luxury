from shared.http.errors import BaseError, LangText


class VendorError(BaseError):
    NOT_FOUND = LangText(zh="廠商不存在", en="Vendor not found")
    DUPLICATE = LangText(zh="廠商名稱重複", en="Vendor name already exists")
    INACTIVE = LangText(zh="廠商已停用，不能新增詢價", en="Vendor is inactive; cannot add quotes")
