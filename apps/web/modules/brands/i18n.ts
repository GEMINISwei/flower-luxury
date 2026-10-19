import { defineMessages } from "@/shared/i18n/dictionary"

export const brandMessages = defineMessages({
  zh: { title: "品牌管理", subtitle: "品牌依名稱排序，所有成員共用", create: "新增品牌",
    name: "品牌名稱", edit: "編輯品牌", save: "儲存", delete: "刪除／停用",
    confirm: "未被引用的品牌會刪除；已有商品使用的品牌會停用。是否繼續？",
    active: "啟用", inactive: "停用", status: "狀態", actions: "操作", empty: "尚無品牌",
    failed: "無法載入品牌", required: "請輸入品牌名稱", saved: "品牌已更新" },
  en: { title: "Brands", subtitle: "Shared brands, sorted by name", create: "New brand",
    name: "Brand name", edit: "Edit brand", save: "Save", delete: "Delete / deactivate",
    confirm: "Unused brands will be deleted. Brands used by products will be deactivated. Continue?",
    active: "Active", inactive: "Inactive", status: "Status", actions: "Actions", empty: "No brands yet",
    failed: "Unable to load brands", required: "Enter a brand name", saved: "Brand updated" },
})
