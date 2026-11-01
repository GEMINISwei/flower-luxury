import { beforeEach, expect, it } from "vitest"
import { readProductFilters, saveProductFilters, productListHref,
  readProductReturnPoint, saveProductReturnPoint } from "@/modules/products/list-state"

beforeEach(() => { localStorage.clear(); sessionStorage.clear() })

it("同裝置只保存商品篩選欄位，清除後不會恢復舊條件", () => {
  expect(readProductFilters(localStorage)).toBeNull()
  saveProductFilters(localStorage, { keyword: " bag ", brand_id: "brand", category: "包包",
    status: "sold", color: "black", year: "2026", cursor: "old", unknown: "ignored" })
  expect(readProductFilters(localStorage)).toEqual({ keyword: "bag", brand_id: "brand",
    category: "包包", status: "sold", color: "black", year: "2026" })
  saveProductFilters(localStorage, {})
  expect(readProductFilters(localStorage)).toEqual({})
  expect(productListHref(new URLSearchParams("keyword=bag&cursor=next&seq=2&unknown=x")))
    .toBe("/products?keyword=bag&cursor=next&seq=2")
})

it("商品返回點保留來源條件分頁與續載深度，拒絕外部網址與異常資料", () => {
  const point = { id: "product-id", href: "/products?keyword=bag&cursor=next&seq=2",
    count: 40, offset: 120 }
  expect(readProductReturnPoint(sessionStorage)).toBeNull()
  saveProductReturnPoint(sessionStorage, point)
  expect(readProductReturnPoint(sessionStorage)).toEqual(point)
  for (const invalid of [
    { ...point, href: "https://example.com" }, { ...point, href: "//example.com" },
    { ...point, href: "/products/another" }, { ...point, count: -1 },
    { ...point, offset: "120" }, { ...point, id: "" },
  ]) {
    saveProductReturnPoint(sessionStorage, invalid as typeof point)
    expect(readProductReturnPoint(sessionStorage)).toBeNull()
  }
})

it("瀏覽器封鎖儲存或資料損壞時仍能使用商品列表", () => {
  const broken = { getItem: () => { throw new Error("blocked") },
    setItem: () => { throw new Error("blocked") } }
  expect(readProductFilters(broken)).toBeNull()
  expect(readProductReturnPoint(broken)).toBeNull()
  expect(() => saveProductFilters(broken, { keyword: "bag" })).not.toThrow()
  expect(() => saveProductReturnPoint(broken,
    { id: "id", href: "/products", count: 20, offset: 0 })).not.toThrow()
  saveProductFilters(localStorage, {})
  const key = localStorage.key(0)!
  localStorage.setItem(key, "{")
  expect(readProductFilters(localStorage)).toBeNull()
  localStorage.setItem(key, "null")
  expect(readProductFilters(localStorage)).toBeNull()
})
