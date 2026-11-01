import { expect, it } from "vitest"
import { brandRemovalAction } from "@/modules/brands/capabilities"

it("品牌列表只允許刪除未引用資料，啟用停用統一由編輯處理", () => {
  expect(brandRemovalAction({ in_use: false, is_active: true })).toBe("delete")
  expect(brandRemovalAction({ in_use: false, is_active: false })).toBe("delete")
  expect(brandRemovalAction({ in_use: true, is_active: true })).toBeNull()
  expect(brandRemovalAction({ in_use: true, is_active: false })).toBeNull()
})
