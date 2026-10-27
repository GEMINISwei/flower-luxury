from shared.http.errors import BaseError, LangText


class ProductError(BaseError):
    NOT_FOUND = LangText(zh="商品不存在", en="Product not found")
    SOLD_LOCKED = LangText(
        zh="已出售商品已鎖定，請先退回", en="Sold product is locked; return it first",
    )
    PHOTO_NOT_FOUND = LangText(zh="照片不存在", en="Photo not found")
    ORIGINAL_UNAVAILABLE = LangText(zh="原圖不可用", en="Original photo unavailable")


class PhotoError(BaseError):
    INVALID = LangText(zh="請選擇有效的 JPEG、PNG、WebP 或 HEIC 照片",
                      en="Choose a valid JPEG, PNG, WebP or HEIC photo")
    TOO_LARGE = LangText(zh="單次照片總容量不可超過 15MB，且檔案不可為空",
                        en="Photo batch must be at most 15MB and files must not be empty")
