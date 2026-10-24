import { expect, it } from "vitest"
import { navRoutes } from "@/config/routes"
import { getMobileNavigation, isMoreActive, splitMobileRoutes } from "@/config/shell/navigation"

it("手機導覽最多三個模組入口，其餘移入更多", () => {
  const routes = ["a", "b", "c", "d", "e"].map((path) => ({ path: `/${path}` }))
  expect(splitMobileRoutes(routes)).toEqual({ primary: routes.slice(0, 3), more: routes.slice(3) })
  expect(splitMobileRoutes(routes.slice(0, 2)))
    .toEqual({ primary: routes.slice(0, 2), more: [] })
  expect(splitMobileRoutes([])).toEqual({ primary: [], more: [] })
})

it("手機導覽沿用區域與權限篩選", () => {
  for (const area of ["user", "admin"] as const) {
    for (const permissions of [[], ["*"]]) {
      const result = getMobileNavigation(area, permissions)
      expect([...result.primary, ...result.more]).toEqual(navRoutes(area, permissions))
      expect(result.primary.length).toBeLessThanOrEqual(3)
    }
  }
})

it("更多涵蓋溢出模組與帳號頁面", () => {
  const routes = [{ path: "/extra" }]
  const entries = [{ kind: "link", href: "/preferences", label: "accountSettings" },
    { kind: "logout", label: "logout" }] as const
  expect(isMoreActive("/extra/detail", routes, entries)).toBe(true)
  expect(isMoreActive("/preferences", routes, entries)).toBe(true)
  expect(isMoreActive("/extras", routes, entries)).toBe(false)
  expect(isMoreActive("/products", routes, entries)).toBe(false)
})
