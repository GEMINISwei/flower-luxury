import { expect, it } from "vitest"
import { brandRemovalAction } from "@/modules/brands/capabilities"

it("未引用品牌可刪除，引用品牌只能停用，已停用引用品牌不提供操作", () => {
  expect(brandRemovalAction({ in_use: false, is_active: true })).toBe("delete")
  expect(brandRemovalAction({ in_use: false, is_active: false })).toBe("delete")
  expect(brandRemovalAction({ in_use: true, is_active: true })).toBe("deactivate")
  expect(brandRemovalAction({ in_use: true, is_active: false })).toBeNull()
})
