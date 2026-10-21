import { expect, it } from "vitest"
import { validateQuote } from "@/modules/products/quote-validation"
import { availableQuoteVendors, quoteCapabilities,
  salePreview } from "@/modules/products/quote-capabilities"

it("詢價依國家驗證正數與小數位數", () => {
  for (const locale of ["zh", "en"] as const) {
    for (const amount of ["", "0", "-1", "NaN", "1.001", "10000000000", "1e2"]) {
      expect(validateQuote(amount, "CN", locale)).toBeTruthy()
    }
    expect(validateQuote("1.01", "TW", locale)).toBeTruthy()
    expect(validateQuote("100", "TW", locale)).toBeUndefined()
    expect(validateQuote("100.00", "TW", locale)).toBeUndefined()
    expect(validateQuote("100.25", "CN", locale)).toBeUndefined()
    expect(validateQuote("0.01", "CN", locale)).toBeUndefined()
    expect(validateQuote("9999999999.99", "CN", locale)).toBeUndefined()
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
  expect(quoteCapabilities("sold", "CN", false)).toEqual({
    canEdit: false, canDelete: false, canRefresh: false, canConfirm: false,
  })
  expect(quoteCapabilities("not_acquired", "TW", false)).toEqual({
    canEdit: true, canDelete: true, canRefresh: false, canConfirm: true,
  })
  expect(quoteCapabilities("not_acquired", "CN", true)).toEqual({
    canEdit: true, canDelete: false, canRefresh: true, canConfirm: true,
  })
})
