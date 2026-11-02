import { defineMessages } from "@/shared/i18n/dictionary"

export const groupMessages = defineMessages({
  zh: {
    title: "群組設定", subtitle: "管理 LINE 商品來源與訊息收集", name: "群組", bot: "Bot 狀態",
    status: "收集狀態", actions: "操作", joined: "已加入", left: "未加入",
    enabled: "已啟用", disabled: "已停用", enable: "啟用收集", disable: "停用收集",
    enableHint: "啟用後會持續收件並保存原圖，依 LINE 原始時間自動整理成商品暫存。",
    collecting: "收集中",
    disableHint: "停用後停止新收件，既有商品暫存仍會保留。",
    review: "確認正式商品", reviewHint: "已建檔商品的來源訊息遭撤回，請人工確認。",
    empty: "尚未發現群組，請將 Bot 邀入群組並傳送訊息。", failed: "無法載入群組，請重試。",
    refresh: "重新整理",
  },
  en: {
    title: "LINE groups", subtitle: "Manage LINE product sources and message collection", name: "Group",
    bot: "Bot status", status: "Collection", actions: "Actions", joined: "Joined",
    left: "Not joined", enabled: "Enabled", disabled: "Disabled",
    enable: "Enable collection", disable: "Disable collection",
    enableHint: "Enabling starts continuous receipt and original photo storage. Messages are grouped into drafts by their original LINE time.",
    collecting: "Collecting",
    disableHint: "New collection stops. Existing product drafts are kept.",
    review: "Review product", reviewHint: "A source message for a created product was withdrawn. Please review it.",
    empty: "No groups discovered. Invite the bot to a group and send a message.",
    failed: "Could not load groups. Please retry.", refresh: "Refresh",
  },
})
