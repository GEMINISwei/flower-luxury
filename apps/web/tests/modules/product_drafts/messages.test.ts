import { expect, it } from "vitest"
import { draftTextMessages } from "@/modules/product_drafts/capabilities"
import type { MessageInfo } from "@/modules/product_drafts/types"

it("暫存原始訊息排除圖片並保留文字原文與順序", () => {
  const base = { draft_id: "draft", external_id: "external", occurred_at: "2026-10-31T01:00:00Z",
    sender_id: "U123", sender_name: null, sequence: 1, source_key: "line:group" }
  const messages: MessageInfo[] = [
    { ...base, id: "photo", kind: "image", text: null },
    { ...base, id: "first", kind: "text", text: " 第一行\n第二行 " },
    { ...base, id: "pending", kind: "image", text: null },
    { ...base, id: "second", kind: "text", text: "成本三萬元" },
  ]
  expect(draftTextMessages(messages)).toEqual([messages[1], messages[3]])
  expect(draftTextMessages(messages.filter((message) => message.kind === "image"))).toEqual([])
  expect(draftTextMessages([])).toEqual([])
  expect(messages).toHaveLength(4)
})
