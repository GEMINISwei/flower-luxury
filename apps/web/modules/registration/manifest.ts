import type { ModuleManifest, ProtectedRoute } from "@/shared/module"

export const REGISTRATION_PATH = "/admin/registration"
export const SIGNUP_PATH = "/signup"

const SETTINGS_ROUTE = {
  path: REGISTRATION_PATH, label: { zh: "註冊碼設定", en: "Registration code" },
  group: "admin", requires: ["*"], navIcon: "registration", showInNav: true,
} as const satisfies ProtectedRoute

export const REGISTRATION_MODULE = {
  name: "registration", protectedRoutes: [SETTINGS_ROUTE],
} as const satisfies ModuleManifest
