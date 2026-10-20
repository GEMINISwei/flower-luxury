import { expect, it } from "vitest"
import { validateRate } from "@/modules/exchange_rates/validation"

it("匯率只接受六位內的正小數", () => {
  for (const locale of ["zh", "en"] as const) {
    for (const value of ["", "0", "-1", "NaN", "Infinity", "1.1234567", "1e2"]) {
      expect(validateRate(value, locale)).toBeTruthy()
    }
    expect(validateRate("4.512345", locale)).toBeUndefined()
    expect(validateRate("4.5", locale)).toBeUndefined()
  }
})
