import { describe, expect, it } from "vitest"
import { navRoutes } from "@/config/routes"
import { getShellRoutes, isShellLinkActive } from "@/config/shell/navigation"

describe("外殼導覽", () => {
  it("一般操作區只包含可見模組，管理區沿用權限篩選", () => {
    for (const permissions of [[], ["*"]]) {
      const routes = getShellRoutes("user", permissions)
      expect(routes).toEqual(navRoutes("user", permissions))
      expect(getShellRoutes("admin", permissions)).toEqual(navRoutes("admin", permissions))
    }
  })

  it("首頁只在根路徑啟用", () => {
    expect(isShellLinkActive("/", "/")).toBe(true)
    expect(isShellLinkActive("/settings", "/")).toBe(false)
    expect(isShellLinkActive("/admin/users", "/")).toBe(false)
  })

  it("子頁沿用所屬導覽且不誤判相似前綴", () => {
    expect(isShellLinkActive("/catalog", "/catalog")).toBe(true)
    expect(isShellLinkActive("/catalog/item/edit", "/catalog")).toBe(true)
    expect(isShellLinkActive("/catalogue", "/catalog")).toBe(false)
    expect(isShellLinkActive("/settings", "/catalog")).toBe(false)
  })
})
