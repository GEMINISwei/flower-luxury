import { expect, it } from "vitest"
import { availableProductBrands, productCapabilities, statusTimeline }
  from "@/modules/products/capabilities"
import { validateProduct } from "@/modules/products/validation"
import type { StatusHistoryInfo } from "@/modules/products/types"

it("已出售商品不可編輯或刪除", () => {
  expect(productCapabilities("sold").canEdit).toBe(false)
  expect(productCapabilities("sold").canDelete).toBe(false)
  expect(productCapabilities("not_acquired").canEdit).toBe(true)
  expect(productCapabilities("not_acquired").canDelete).toBe(true)
})

it("商品表單只提供啟用品牌但保留原品牌", () => {
  const brands = [{ id: "active", is_active: true }, { id: "old", is_active: false }]
  expect(availableProductBrands(brands).map((brand) => brand.id)).toEqual(["active"])
  expect(availableProductBrands(brands, "old").map((brand) => brand.id))
    .toEqual(["active", "old"])
})

it("商品必填與成本驗證提供中英文錯誤", () => {
  for (const locale of ["zh", "en"] as const) {
    const invalid = validateProduct({
      name: " ", brand_id: "", category: "", cost_price: "-1", year: "10000",
    }, locale)
    expect(Object.keys(invalid)).toEqual(["name", "brand_id", "category", "cost_price", "year"])
    expect(invalid.cost_price).toBe(locale === "zh"
      ? "請輸入 0 至 2147483647 的整數成本" : "Enter an integer cost from 0 to 2147483647")
    expect(validateProduct({
      name: "Bag", brand_id: "brand", category: "包包", cost_price: "0", year: "",
    }, locale)).toEqual({})
  }
})

it("流向依時間排列並保留既有原因", () => {
  const created = "2026-10-20T01:00:00Z"
  const sale: StatusHistoryInfo = { id: "sale", changed_at: "2026-10-21T01:00:00Z",
    from_status: "not_acquired", to_status: "sold", action: "sale", reason: "existing",
    changed_by: "actor", operator_name: "店長" }
  const rows = statusTimeline([sale], created)
  expect(rows.map((row) => row.to_status)).toEqual(["not_acquired", "sold"])
  expect(rows[0]).toMatchObject({ action: "create", from_status: null, changed_at: created })
  expect(rows[1]).toEqual(sale)
  const initial: StatusHistoryInfo = { ...rows[0], id: "real-create" }
  expect(statusTimeline([sale, initial], created)).toEqual([initial, sale])
  expect(statusTimeline([], created)).toHaveLength(1)
})
