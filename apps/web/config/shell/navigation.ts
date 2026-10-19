import { appMessages } from "@/config/i18n"
import { navRoutes } from "@/config/routes"
import type { RouteArea } from "@/shared/module"

const HOME_ROUTE = {
  path: "/",
  navIcon: "home",
  label: { zh: appMessages.zh.homeTitle, en: appMessages.en.homeTitle },
} as const

export function getShellRoutes(area: RouteArea, permissions: readonly string[]) {
  const routes = navRoutes(area, permissions)
  return area === "user" ? [HOME_ROUTE, ...routes] : routes
}

/** 根路徑是所有網址的前綴, 必須精確比對才能避免首頁一直顯示為選中。 */
export function isShellLinkActive(pathname: string, href: string) {
  return pathname === href || (href !== "/" && pathname.startsWith(`${href}/`))
}
