from shared.http.errors import BaseError, LangText


class DraftError(BaseError):
    INVALID_SALE_QUOTE = LangText(zh="選定的成交報價已不存在，請重新選擇。",
                                  en="The selected sale quote is unavailable. Select it again.")

    NOT_READY = LangText(zh="商品仍在收集、處理中或有待確認訊息，暫時無法審核建檔。",
                         en="Collection, processing or message review must finish before approval.")
    INVALID_TARGET = LangText(zh="請選擇可整理的目標商品。",
                              en="Choose an editable target draft.")
    PREFILL_UNAVAILABLE = LangText(
        zh="AI 預填暫時無法使用，請確認金鑰或稍後重試。",
        en="AI prefill is unavailable. Check the API key or retry later.")

    DUPLICATE_QUOTE = LangText(
        zh="同一廠商只能有一筆詢價。", en="Only one quote per vendor is allowed.")

    NOT_FOUND = LangText(
        zh="找不到暫存商品或訊息",
        en="Draft product or message not found")

    STALE = LangText(
        zh="資料已變更，請重新載入後再確認",
        en="Data has changed; reload and confirm again")

    INVALID_FIELDS = LangText(
        zh="請完整填寫商品必填欄位",
        en="Complete all required product fields")

    PHOTO_NOT_READY = LangText(
        zh="請確認至少一張照片且所有照片已就緒",
        en="At least one photo is required and all photos must be ready")

    INVALID_PHOTOS = LangText(
        zh="照片不屬於此商品或排序不完整",
        en="Photos do not belong to this draft or the order is incomplete")

    DIFFERENT_SOURCE = LangText(
        zh="只能移動同一群組的訊息",
        en="Messages can only move within the same group")
