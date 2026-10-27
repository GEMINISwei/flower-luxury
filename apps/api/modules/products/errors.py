from shared.http.errors import BaseError, LangText


class ProductError(BaseError):
    NOT_FOUND = LangText(zh="商品不存在", en="Product not found")
    INVALID_TRANSITION = LangText(zh="不允許此狀態轉換", en="This status transition is not allowed")
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


class QuoteError(BaseError):
    NOT_FOUND = LangText(zh="詢價不存在或不屬於此商品", en="Quote not found for this product")
    DUPLICATE = LangText(
        zh="此廠商已有詢價，請修改既有報價", en="This vendor already has a quote; edit it instead",
    )
    AMOUNT = LangText(
        zh="報價須大於零；臺幣為整數，人民幣最多兩位小數，且金額不可超出範圍",
        en="Quote must be positive: whole TWD or up to two CNY decimals, within the amount limit",
    )
    NO_RATE = LangText(zh="請先由店長設定人民幣匯率", en="Ask a manager to set the CNY rate first")
    REFERENCED = LangText(
        zh="曾用於成交的詢價不能刪除", en="A previously sold quote cannot be deleted",
    )
    STALE = LangText(
        zh="報價或成本已變動，請重新載入後確認成交",
        en="Quote or cost changed; reload before confirming the sale",
    )
