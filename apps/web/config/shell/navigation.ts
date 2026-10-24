import { navRoutes } from "@/config/routes"
import type { RouteArea } from "@/shared/module"
import type { AccountMenuEntry } from "./account-menu"

export function getShellRoutes(area: RouteArea, permissions: readonly string[]) {
  return navRoutes(area, permissions)
}

export function splitMobileRoutes<T>(routes: readonly T[]) {
  return { primary: routes.slice(0, 3), more: routes.slice(3) }
}

export function getMobileNavigation(area: RouteArea, permissions: readonly string[]) {
  return splitMobileRoutes(getShellRoutes(area, permissions))
}

export function isMoreActive(
  pathname: string, routes: readonly { path: string }[], entries: readonly AccountMenuEntry[],
) {
  return routes.some((route) => isShellLinkActive(pathname, route.path))
    || entries.some((entry) => entry.kind === "link" && isShellLinkActive(pathname, entry.href))
}

/** 根路徑是所有網址的前綴, 必須精確比對才能避免首頁一直顯示為選中。 */
export function isShellLinkActive(pathname: string, href: string) {
  return pathname === href || (href !== "/" && pathname.startsWith(`${href}/`))
}
