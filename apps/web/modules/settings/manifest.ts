import type { ModuleManifest, ProtectedRoute } from "@/shared/module"

const SETTINGS_ROUTE = {
  path: "/settings", label: { zh: "用戶設定", en: "User settings" }, group: "user", requires: [], navIcon: "settings", showInNav: false,
} as const satisfies ProtectedRoute

export const SETTINGS_MODULE = {
  name: "settings",
  protectedRoutes: [SETTINGS_ROUTE],
} as const satisfies ModuleManifest

export const SYSTEM_SETTINGS_PATH = `${SETTINGS_ROUTE.path}/system`
