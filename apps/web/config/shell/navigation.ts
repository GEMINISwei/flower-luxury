import { navRoutes } from "@/config/routes"
import type { RouteArea } from "@/shared/module"

export function getShellRoutes(area: RouteArea, permissions: readonly string[]) {
  return navRoutes(area, permissions)
}

/** 根路徑是所有網址的前綴, 必須精確比對才能避免首頁一直顯示為選中。 */
export function isShellLinkActive(pathname: string, href: string) {
  return pathname === href || (href !== "/" && pathname.startsWith(`${href}/`))
}
