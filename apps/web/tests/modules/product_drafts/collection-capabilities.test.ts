import { describe, expect, it } from "vitest"
import { collectionCapabilities, draftStage } from "@/modules/product_drafts/capabilities"

describe("人工完成與定稿", () => {
  it("只有目前有訊息的收集輪次可完成，圖片下載中仍可先確認分組", () => {
    expect(collectionCapabilities({ id: null, message_count: 0 }).canComplete).toBe(false)
    expect(collectionCapabilities({ id: "round", message_count: 0 }).canComplete).toBe(false)
    expect(collectionCapabilities({ id: "round", message_count: 2 }).canComplete).toBe(true)
  })
  it("未定稿商品進入分組確認，定稿後才依處理狀態進入審核", () => {
    expect(draftStage({ collecting: false, requires_finalization: true })).toBe("needsFinalization")
    expect(draftStage({ collecting: false, requires_finalization: false, processing: true }))
      .toBe("processing")
    expect(draftStage({ collecting: false, requires_finalization: false })).toBe("waiting")
  })
})
