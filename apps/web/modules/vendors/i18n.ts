import { defineMessages } from "@/shared/i18n/dictionary"

export const vendorMessages = defineMessages({
  zh: {
    title: "廠商", subtitle: "管理共用廠商與備註", create: "新增廠商",
    entity: "廠商", edit: "編輯", save: "儲存", name: "名稱", note: "備註",
    status: "狀態", active: "啟用", inactive: "停用",
    actions: "操作", delete: "刪除", empty: "尚無廠商", failed: "無法載入廠商資料",
    required: "請填寫廠商名稱",
    confirmDelete: "確定刪除此廠商？刪除後無法還原。",
  },
  en: {
    title: "Vendors", subtitle: "Manage shared vendors and notes",
    create: "New vendor", entity: "Vendor", edit: "Edit", save: "Save", name: "Name",
    note: "Notes",
    status: "Status", active: "Active", inactive: "Inactive", actions: "Actions",
    delete: "Delete", empty: "No vendors yet", failed: "Unable to load vendors",
    required: "Enter a vendor name",
    confirmDelete: "Delete this vendor? This cannot be undone.",
  },
})
