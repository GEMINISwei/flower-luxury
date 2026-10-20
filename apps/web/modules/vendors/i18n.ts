import { defineMessages } from "@/shared/i18n/dictionary"

export const vendorMessages = defineMessages({
  zh: {
    title: "廠商管理", subtitle: "共用廠商與固定國家幣別", create: "新增廠商",
    edit: "編輯廠商", save: "儲存廠商", name: "名稱", country: "國家", note: "備註",
    TW: "臺灣（TWD）", CN: "中國（CNY）", status: "狀態", active: "啟用", inactive: "停用",
    actions: "操作", delete: "刪除／停用", empty: "尚無廠商", failed: "無法載入廠商資料",
    required: "請填寫廠商名稱", countryInvalid: "請選擇臺灣或中國",
    countryLocked: "此廠商曾有詢價，國家已鎖定。", currencyHint: "幣別由國家決定，不能自行調整。",
    confirm: "確定刪除此廠商？曾有詢價的廠商會改為停用並保留歷史。",
  },
  en: {
    title: "Vendors", subtitle: "Shared vendors with currencies determined by country",
    create: "New vendor", edit: "Edit vendor", save: "Save vendor", name: "Name",
    country: "Country", note: "Notes", TW: "Taiwan (TWD)", CN: "China (CNY)",
    status: "Status", active: "Active", inactive: "Inactive", actions: "Actions",
    delete: "Delete / deactivate", empty: "No vendors yet", failed: "Unable to load vendors",
    required: "Enter a vendor name", countryInvalid: "Select Taiwan or China",
    countryLocked: "This vendor has quote history. Its country is locked.",
    currencyHint: "Currency is determined by country and cannot be changed independently.",
    confirm: "Delete this vendor? Vendors with quote history will be deactivated and retained.",
  },
})
