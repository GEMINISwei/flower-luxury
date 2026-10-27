import { expect, it } from "vitest"
import { productCapabilities } from "@/modules/products/capabilities"
import { validateReturnReason } from "@/modules/products/validation"

it("已出售商品提供退回且恢復編輯前必須有原因", () => {
  expect(productCapabilities("sold").canReturn).toBe(true)
  expect(productCapabilities("not_acquired").canReturn).toBe(false)
  for (const locale of ["zh", "en"] as const) {
    expect(validateReturnReason("", locale)).toBeTruthy()
    expect(validateReturnReason("   ", locale)).toBeTruthy()
    expect(validateReturnReason("退貨", locale)).toBeUndefined()
  }
})
