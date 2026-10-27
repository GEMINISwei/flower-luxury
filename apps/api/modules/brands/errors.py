from shared.http.errors import BaseError, LangText


class BrandError(BaseError):
    NOT_FOUND = LangText(zh="品牌不存在", en="Brand not found")
    DUPLICATE = LangText(zh="品牌名稱重複", en="Brand name already exists")
    INACTIVE = LangText(
        zh="品牌已停用，請選擇其他品牌", en="Brand is inactive; choose another brand",
    )
