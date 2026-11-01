import { expect, it } from "vitest"
import { formatQuoteNumbers } from "@/modules/products/quote-format"

it("詢價報價顯示整數並以千分位分隔，匯率固定顯示兩位小數", () => {
  expect(formatQuoteNumbers("12345.00", "4.500000"))
    .toEqual({ amount: "12,345", rate: "4.50" })
  expect(formatQuoteNumbers("100.00", "1.000000"))
    .toEqual({ amount: "100", rate: "1.00" })
})

it("詢價數字依顯示位數四捨五入且不限制大匯率的整數位數", () => {
  expect(formatQuoteNumbers("1234.56", "1.235000"))
    .toEqual({ amount: "1,235", rate: "1.24" })
  expect(formatQuoteNumbers("9999999999.99", "12345.678901"))
    .toEqual({ amount: "10,000,000,000", rate: "12345.68" })
})
