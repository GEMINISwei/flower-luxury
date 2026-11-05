import { beforeEach, expect, it } from "vitest"
import { draftListHref, draftReturnHref, saveDraftReturnPoint }
  from "@/modules/product_drafts/list-state"

const fallback = "/product-drafts?source_key=line%3Aa"
const paged = "/product-drafts?source_key=line%3Aa&cursor=next&direction=next&seq=2"

beforeEach(() => sessionStorage.clear())

it("列表網址保留來源與分頁，不帶審核完成的一次性提示", () => {
  expect(draftListHref(new URLSearchParams(
    "source_key=line%3Aa&cursor=next&direction=next&seq=2&created=product&completed=1&x=1")))
    .toBe(paged)
  expect(draftListHref(new URLSearchParams("created=product"))).toBe("/product-drafts")
})

it("從列表進入的那一筆返回原分頁，其他筆與沒有紀錄時回預設列表", () => {
  expect(draftReturnHref(sessionStorage, "draft-id", fallback)).toBe(fallback)
  saveDraftReturnPoint(sessionStorage, { id: "draft-id", href: paged })
  expect(draftReturnHref(sessionStorage, "draft-id", fallback)).toBe(paged)
  expect(draftReturnHref(sessionStorage, "another-id", fallback)).toBe(fallback)
})

it("暫存返回點拒絕外部網址與異常資料", () => {
  for (const invalid of ["https://example.com", "//example.com", "/product-drafts/another",
    "/products?seq=2", "/product-drafts?next=https://example.com", 2]) {
    saveDraftReturnPoint(sessionStorage, { id: "draft-id", href: invalid as string })
    expect(draftReturnHref(sessionStorage, "draft-id", fallback)).toBe(fallback)
  }
})

it("瀏覽器封鎖儲存時仍能返回預設列表", () => {
  const broken = { getItem: () => { throw new Error("blocked") },
    setItem: () => { throw new Error("blocked") } }
  expect(draftReturnHref(broken, "draft-id", fallback)).toBe(fallback)
  expect(draftReturnHref(null, "draft-id", fallback)).toBe(fallback)
  expect(() => saveDraftReturnPoint(broken, { id: "draft-id", href: paged })).not.toThrow()
})
