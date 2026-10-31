import { expect, it } from "vitest"
import { validateVendor } from "@/modules/vendors/validation"

it("廠商表單提供中英文驗證且不需要國家", () => {
  for (const locale of ["zh", "en"] as const) {
    expect(validateVendor({ name: " " }, locale)).toEqual({ name: expect.any(String) })
    expect(validateVendor({ name: "Buyer" }, locale)).toEqual({})
  }
})
