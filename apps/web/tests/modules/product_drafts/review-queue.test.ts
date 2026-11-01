import { expect, it } from "vitest"
import { draftQueueHref, draftStage } from "@/modules/product_drafts/capabilities"

it("收集中處理中與待確認不能進入審核", () => {
  expect(draftStage({ collecting: true })).toBe("collecting")
  expect(draftStage({ collecting: false, processing: true })).toBe("processing")
  expect(draftStage({ collecting: false, needs_confirmation: true })).toBe("needsConfirmation")
  expect(draftStage({ collecting: false })).toBe("waiting")
})

it("連續審核與返回連結保留群組範圍與上一筆建檔連結", () => {
  expect(draftQueueHref("draft-id", "line:group-a", "product-id"))
    .toBe("/product-drafts/draft-id?source_key=line%3Agroup-a&created=product-id")
  expect(draftQueueHref(undefined, "line:group-a"))
    .toBe("/product-drafts?source_key=line%3Agroup-a")
  expect(draftQueueHref()).toBe("/product-drafts")
})
