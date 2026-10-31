import { expect, it } from "vitest"
import { validateQuote } from "@/modules/products/quote-validation"
import { availableQuoteVendors, quoteCapabilities,
  salePreview } from "@/modules/products/quote-capabilities"

it("詢價驗證報價與逐筆匯率", () => {
  for (const locale of ["zh", "en"] as const) {
    for (const amount of ["", "0", "-1", "NaN", "1.001", "10000000000", "1e2"]) {
      expect(validateQuote(amount, "1", locale)).toBeTruthy()
    }
    for (const rate of ["", "0", "-1", "NaN", "1.0000001", "10000000000", "1e2"]) {
      expect(validateQuote("100", rate, locale)).toBeTruthy()
    }
    expect(validateQuote("1.01", "1", locale)).toBeUndefined()
    expect(validateQuote("100.25", "4.512345", locale)).toBeUndefined()
    expect(validateQuote("9999999999.99", "1", locale)).toBeUndefined()
    expect(validateQuote("9999999999.99", "9999999999.999999", locale)).toBeTruthy()
  }
})

it("詢價表單排除已報價與停用廠商", () => {
  const vendors = [
    { id: "used", is_active: true }, { id: "new", is_active: true },
    { id: "inactive", is_active: false },
  ]
  expect(availableQuoteVendors(vendors, [{ vendor_id: "used" }])).toEqual([vendors[1]])
  expect(availableQuoteVendors(vendors, [])).toEqual([vendors[0], vendors[1]])
})

it("成交確認依臺幣金額與成本顯示利潤或虧損", () => {
  expect(salePreview(452, 800)).toEqual({ profit: -348, loss: 348, isLoss: true })
  expect(salePreview(800, 800)).toEqual({ profit: 0, loss: 0, isLoss: false })
  expect(salePreview(1027, 800)).toEqual({ profit: 227, loss: 0, isLoss: false })
})

it("詢價操作遵守售出鎖定與成交引用保護", () => {
  expect(quoteCapabilities("sold", false)).toEqual({
    canEdit: false, canDelete: false, canConfirm: false,
  })
  expect(quoteCapabilities("not_acquired", false)).toEqual({
    canEdit: true, canDelete: true, canConfirm: true,
  })
  expect(quoteCapabilities("not_acquired", true)).toEqual({
    canEdit: true, canDelete: false, canConfirm: true,
  })
})
