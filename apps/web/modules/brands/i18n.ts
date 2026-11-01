import { defineMessages } from "@/shared/i18n/dictionary"

export const brandMessages = defineMessages({
  zh: { title: "品牌", subtitle: "品牌依名稱排序，所有成員共用", create: "新增品牌",
    name: "名稱", entity: "品牌", edit: "編輯", save: "儲存", delete: "刪除",
    confirmDelete: "確定刪除此品牌？刪除後無法還原。",
    active: "啟用", inactive: "停用", status: "狀態", actions: "操作", empty: "尚無品牌",
    failed: "無法載入品牌", required: "請輸入品牌名稱", saved: "品牌已更新" },
  en: { title: "Brands", subtitle: "Shared brands, sorted by name", create: "New brand",
    name: "Name", entity: "Brand", edit: "Edit", save: "Save", delete: "Delete",
    confirmDelete: "Delete this brand? This cannot be undone.",
    active: "Active", inactive: "Inactive", status: "Status", actions: "Actions", empty: "No brands yet",
    failed: "Unable to load brands", required: "Enter a brand name", saved: "Brand updated" },
})
