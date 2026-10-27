import { expect, it } from "vitest"
import { validateVendor } from "@/modules/vendors/validation"

it("廠商表單提供中英文驗證", () => {
  for (const locale of ["zh", "en"] as const) {
    expect(validateVendor({ name: " ", country: "US" }, locale)).toEqual({
      name: expect.any(String), country: expect.any(String),
    })
    expect(validateVendor({ name: "Buyer", country: "TW" }, locale)).toEqual({})
    expect(validateVendor({ name: "Buyer", country: "CN" }, locale)).toEqual({})
  }
})
