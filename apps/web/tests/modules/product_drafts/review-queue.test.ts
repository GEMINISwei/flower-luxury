import { expect, it } from "vitest"
import { draftQueueHref } from "@/modules/product_drafts/capabilities"

it("連續審核與返回連結保留群組範圍與上一筆建檔連結", () => {
  expect(draftQueueHref("draft-id", "line:group-a", "product-id"))
    .toBe("/product-drafts/draft-id?source_key=line%3Agroup-a&created=product-id")
  expect(draftQueueHref(undefined, "line:group-a"))
    .toBe("/product-drafts?source_key=line%3Agroup-a")
  expect(draftQueueHref()).toBe("/product-drafts")
})
