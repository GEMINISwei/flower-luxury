from shared.http.errors import BaseError, LangText


class LineError(BaseError):
    DISABLED = LangText(zh="尚未設定 LINE 收件", en="LINE collection is not configured")
    SIGNATURE = LangText(zh="LINE 簽章無效", en="Invalid LINE signature")
    PAYLOAD = LangText(zh="LINE 事件格式無效", en="Invalid LINE event payload")
    TOO_LARGE = LangText(zh="LINE 事件超過大小上限", en="LINE payload exceeds the size limit")
    NOT_FOUND = LangText(zh="找不到 LINE 群組", en="LINE group not found")
    LEFT = LangText(zh="Bot 已離開此群組，請重新邀請入群", en="Invite the bot back before enabling")
