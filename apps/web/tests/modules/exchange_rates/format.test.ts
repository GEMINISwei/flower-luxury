import { expect, it } from "vitest"
import { formatRate } from "@/modules/exchange_rates/format"
import { validateRate } from "@/modules/exchange_rates/validation"

it("匯率設定四捨五入為兩位小數", () => {
  for (const [input, output] of [
    ["4.500000", "4.50"], ["4.567890", "4.57"], ["4", "4.00"],
    ["1.005", "1.01"], ["9999999999.994999", "9999999999.99"],
  ]) expect(formatRate(input)).toBe(output)
  expect(formatRate(null)).toBe("")
  expect(formatRate("")).toBe("")
})

it("不將無效輸入轉為可儲存的匯率，四捨五入為零仍無效", () => {
  for (const value of ["abc", "-1", "1e2", "1.1234567"]) {
    expect(formatRate(value)).toBe(value)
    expect(validateRate(formatRate(value), "zh")).toBeTruthy()
  }
  expect(validateRate(formatRate("0.001"), "en")).toBeTruthy()
})
