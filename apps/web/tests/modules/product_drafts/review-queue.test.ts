import { expect, it } from "vitest"
import { draftPageHref, draftQueueHref } from "@/modules/product_drafts/capabilities"

it("返回連結指向該筆所在的分頁，第一頁不帶分頁參數", () => {
  expect(draftPageHref("line:group-a", { cursor: "next=", seq: 3 }))
    .toBe("/product-drafts?source_key=line%3Agroup-a&cursor=next%3D&direction=next&seq=3")
  expect(draftPageHref(undefined, { cursor: "next=", seq: 2 }))
    .toBe("/product-drafts?cursor=next%3D&direction=next&seq=2")
  expect(draftPageHref("line:group-a", { cursor: null, seq: 1 }))
    .toBe("/product-drafts?source_key=line%3Agroup-a")
  expect(draftPageHref(undefined, { cursor: null, seq: 1 })).toBe("/product-drafts")
})

it("連續審核與返回連結保留群組範圍與上一筆建檔連結", () => {
  expect(draftQueueHref("draft-id", "line:group-a", "product-id"))
    .toBe("/product-drafts/draft-id?source_key=line%3Agroup-a&created=product-id")
  expect(draftQueueHref(undefined, "line:group-a"))
    .toBe("/product-drafts?source_key=line%3Agroup-a")
  expect(draftQueueHref()).toBe("/product-drafts")
})
