import { expect, it } from "vitest"
import { vendorRemovalAction } from "@/modules/vendors/capabilities"

it("廠商列表只允許刪除未詢價資料，啟用停用統一由編輯處理", () => {
  expect(vendorRemovalAction({ has_quotes: false, is_active: true })).toBe("delete")
  expect(vendorRemovalAction({ has_quotes: false, is_active: false })).toBe("delete")
  expect(vendorRemovalAction({ has_quotes: true, is_active: true })).toBeNull()
  expect(vendorRemovalAction({ has_quotes: true, is_active: false })).toBeNull()
})
