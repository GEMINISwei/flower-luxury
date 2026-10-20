import { expect, it } from "vitest"
import { validateQuote } from "@/modules/products/quote-validation"
import { quoteCapabilities } from "@/modules/products/quote-capabilities"

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

it("詢價操作遵守售出鎖定與成交引用保護", () => {
  expect(quoteCapabilities("sold", "CN", false)).toEqual({
    canEdit: false, canDelete: false, canRefresh: false, canConfirm: false,
  })
  expect(quoteCapabilities("in_stock", "TW", false)).toEqual({
    canEdit: true, canDelete: true, canRefresh: false, canConfirm: true,
  })
  expect(quoteCapabilities("not_acquired", "CN", true)).toEqual({
    canEdit: true, canDelete: false, canRefresh: true, canConfirm: true,
  })
})
