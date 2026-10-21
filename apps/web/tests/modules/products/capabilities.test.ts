import { expect, it } from "vitest"
import { productCapabilities } from "@/modules/products/capabilities"
import { validatePhotoBatch, validateProduct } from "@/modules/products/validation"

it("未收購可編輯刪除，已出售只允許退回", () => {
  expect(productCapabilities("sold")).toEqual({
    canEdit: false, canDelete: false, canReturn: true,
  })
  expect(productCapabilities("not_acquired")).toEqual({
    canEdit: true, canDelete: true, canReturn: false,
  })
})

it("照片總容量上限為 15 MiB 且不限制張數", () => {
  const file = (size: number) => ({ size, name: "photo.heic", type: "image/heic" })
  expect(validatePhotoBatch([file(15 * 1024 * 1024)], "zh")).toBeUndefined()
  expect(validatePhotoBatch(Array.from({ length: 50 }, () => file(100)), "en"))
    .toBeUndefined()
  expect(validatePhotoBatch([file(8 * 1024 * 1024), file(8 * 1024 * 1024)], "zh"))
    .toBeTruthy()
  expect(validatePhotoBatch([], "en")).toBeTruthy()
  expect(validatePhotoBatch([{ size: 1, name: "bad.svg", type: "image/svg+xml" }], "en"))
    .toBeTruthy()
})

it("商品必填與成本驗證提供中英文錯誤", () => {
  const form = { name: " ", brand_id: "", category: "", cost_price: "-1", year: "bad" }
  for (const locale of ["zh", "en"] as const) {
    const errors = validateProduct(form, locale)
    expect(errors.name).toBeTruthy()
    expect(errors.brand_id).toBeTruthy()
    expect(errors.category).toBeTruthy()
    expect(errors.cost_price).toBeTruthy()
    expect(errors.year).toBeTruthy()
    expect(validateProduct({
      name: "包包", brand_id: "id", category: "包包", cost_price: "0", year: "",
    }, locale)).toEqual({})
  }
})
