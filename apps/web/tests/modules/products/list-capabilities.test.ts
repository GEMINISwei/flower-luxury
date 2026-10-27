import { expect, it } from "vitest"
import { appendProducts, canLoadMoreProducts, productListQuery }
  from "@/modules/products/capabilities"

it("續載只保留有效商品篩選，不能覆寫游標與批次大小", () => {
  expect(productListQuery({ keyword: "bag", brand_id: "brand", category: "包包",
    status: "sold", color: "black", year: "2024", limit: "999", cursor: "wrong" }))
    .toEqual({ keyword: "bag", brand_id: "brand", category: "包包",
      status: "sold", color: "black", year: "2024" })
  expect(productListQuery({ keyword: "", status: "" })).toEqual({})
})

it("僅手機捲到列表底部且還有下一批時續載", () => {
  const ready = { mobile: true, intersecting: true, loading: false, errorMessage: "",
    hasNext: true, nextCursor: "next" }
  expect(canLoadMoreProducts(ready)).toBe(true)
  for (const blocked of [{ mobile: false }, { intersecting: false }, { loading: true },
    { errorMessage: "failed" }, { hasNext: false }, { nextCursor: null }]) {
    expect(canLoadMoreProducts({ ...ready, ...blocked })).toBe(false)
  }
})

it("下一批商品附加於原列表並略過重複商品", () => {
  const current = [{ id: "one", name: "first" }]
  expect(appendProducts(current, [{ id: "one", name: "duplicate" },
    { id: "two", name: "second" }, { id: "two", name: "duplicate" }]))
    .toEqual([{ id: "one", name: "first" }, { id: "two", name: "second" }])
  expect(current).toEqual([{ id: "one", name: "first" }])
})
