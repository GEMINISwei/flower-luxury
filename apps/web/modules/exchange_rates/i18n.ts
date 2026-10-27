import { defineMessages } from "@/shared/i18n/dictionary"

export const exchangeMessages = defineMessages({
  zh: { title: "匯率設定", subtitle: "設定人民幣換算新臺幣的匯率", label: "1 CNY（人民幣）＝多少 TWD（新臺幣）",
    unconfigured: "尚未設定匯率", current: "目前匯率：1 CNY ＝ {rate} TWD", save: "儲存匯率",
    saving: "儲存中…", saved: "匯率已儲存", failed: "無法讀取匯率設定",
    invalid: "請輸入大於 0、最多六位小數且整數部分最多十位的匯率",
    hint: "匯率四捨五入至小數點後兩位。日後詢價會保存當次匯率；更改這裡不會回寫歷史金額。", updated: "最後設定：{name} · {time}" },
  en: { title: "Exchange rate", subtitle: "Set the Chinese yuan to Taiwan dollar rate",
    label: "1 CNY (Chinese yuan) equals how many TWD (Taiwan dollars)",
    unconfigured: "Exchange rate is not set", current: "Current rate: 1 CNY = {rate} TWD",
    save: "Save rate", saving: "Saving…", saved: "Exchange rate saved", failed: "Unable to load exchange rate",
    invalid: "Enter a positive rate with up to six decimal places and ten integer digits",
    hint: "Rates are rounded to two decimal places. Future quotes save their own rate; history stays unchanged.",
    updated: "Last set: {name} · {time}" },
})
