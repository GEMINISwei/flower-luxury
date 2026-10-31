import { expect, it } from "vitest"
import { vendorRemovalAction } from "@/modules/vendors/capabilities"

it("未詢價廠商可刪除，有詢價廠商只能停用，已停用且有詢價時不提供操作", () => {
  expect(vendorRemovalAction({ has_quotes: false, is_active: true })).toBe("delete")
  expect(vendorRemovalAction({ has_quotes: false, is_active: false })).toBe("delete")
  expect(vendorRemovalAction({ has_quotes: true, is_active: true })).toBe("deactivate")
  expect(vendorRemovalAction({ has_quotes: true, is_active: false })).toBeNull()
})
