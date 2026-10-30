import { defineMessages } from "@/shared/i18n/dictionary"

export const groupMessages = defineMessages({
  zh: {
    title: "群組設定", subtitle: "管理 LINE 商品來源與訊息收集", name: "群組", bot: "Bot 狀態",
    status: "收集狀態", actions: "操作", joined: "已加入", left: "已退群，請重新邀請 Bot",
    enabled: "已啟用", disabled: "已停用", enable: "啟用收集", disable: "停用收集",
    enableHint: "啟用後請於群組傳送 /start 開始收集，傳送 /end 結束批次。",
    collecting: "收集中", waiting: "等待 /start", stop: "結束批次",
    stopHint: "結束目前批次並停止新收件，已排入的圖片下載將繼續完成。",
    batchStart: "批次開始", batchEnd: "批次結束", issueCount: "批次異常：{count} 筆",
    replyFailed: "指令回覆未送達，請以此處顯示的收集狀態為準。",
    disableHint: "停用後停止新收件，既有商品暫存仍會保留。",
    review: "確認正式商品", reviewHint: "已建檔商品的來源訊息遭撤回，請人工確認。",
    empty: "尚未發現群組，請將 Bot 邀入群組並傳送訊息。", failed: "無法載入群組，請重試。",
    refresh: "重新整理",
  },
  en: {
    title: "LINE groups", subtitle: "Manage LINE product sources and message collection", name: "Group",
    bot: "Bot status", status: "Collection", actions: "Actions", joined: "Joined",
    left: "Left; invite the bot back", enabled: "Enabled", disabled: "Disabled",
    enable: "Enable collection", disable: "Disable collection",
    enableHint: "After enabling, send /start in the group to collect and /end to finish the batch.",
    collecting: "Collecting", waiting: "Waiting for /start", stop: "End batch",
    stopHint: "End the current batch. Queued image downloads will continue.",
    batchStart: "Batch started", batchEnd: "Batch ended", issueCount: "Batch issues: {count}",
    replyFailed: "The command reply was not delivered. Use the collection state shown here.",
    disableHint: "New collection stops. Existing product drafts are kept.",
    review: "Review product", reviewHint: "A source message for a created product was withdrawn. Please review it.",
    empty: "No groups discovered. Invite the bot to a group and send a message.",
    failed: "Could not load groups. Please retry.", refresh: "Refresh",
  },
})
