import { defineMessages } from "@/shared/i18n/dictionary"

export const vendorMessages = defineMessages({
  zh: {
    title: "廠商", subtitle: "共用廠商與固定國家幣別", create: "新增廠商",
    entity: "廠商", edit: "編輯", save: "儲存", name: "名稱", country: "國家", note: "備註",
    TW: "臺灣（TWD）", CN: "中國（CNY）", status: "狀態", active: "啟用", inactive: "停用",
    actions: "操作", delete: "刪除", deactivate: "停用", empty: "尚無廠商", failed: "無法載入廠商資料",
    required: "請填寫廠商名稱", countryInvalid: "請選擇臺灣或中國",
    countryLocked: "此廠商曾有詢價，國家已鎖定。", currencyHint: "幣別由國家決定，不能自行調整。",
    confirmDelete: "確定刪除此廠商？刪除後無法還原。",
    confirmDeactivate: "確定停用此廠商？詢價與成交歷史會保留。",
  },
  en: {
    title: "Vendors", subtitle: "Shared vendors with currencies determined by country",
    create: "New vendor", entity: "Vendor", edit: "Edit", save: "Save", name: "Name",
    country: "Country", note: "Notes", TW: "Taiwan (TWD)", CN: "China (CNY)",
    status: "Status", active: "Active", inactive: "Inactive", actions: "Actions",
    delete: "Delete", deactivate: "Deactivate", empty: "No vendors yet", failed: "Unable to load vendors",
    required: "Enter a vendor name", countryInvalid: "Select Taiwan or China",
    countryLocked: "This vendor has quote history. Its country is locked.",
    currencyHint: "Currency is determined by country and cannot be changed independently.",
    confirmDelete: "Delete this vendor? This cannot be undone.",
    confirmDeactivate: "Deactivate this vendor? Quote and sale history will be retained.",
  },
})
