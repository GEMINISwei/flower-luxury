import { expect, it } from "vitest"
import { photoCapabilities } from "@/modules/products/capabilities"

it("未收購的其他照片可以設主圖及刪除", () => {
  expect(photoCapabilities("not_acquired", false)).toEqual({ canSetMain: true, canDelete: true })
})

it("主圖不提供設主圖或刪除操作", () => {
  expect(photoCapabilities("not_acquired", true)).toEqual({ canSetMain: false, canDelete: false })
})

it("已出售商品所有照片均不可修改", () => {
  for (const main of [true, false]) {
    expect(photoCapabilities("sold", main)).toEqual({ canSetMain: false, canDelete: false })
  }
})
