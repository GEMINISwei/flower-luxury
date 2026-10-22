import type { ModuleManifest, ProtectedRoute } from "@/shared/module"

const BRANDS_ROUTE = {
  path: "/brands", label: { zh: "品牌", en: "Brands" },
  group: "user", requires: [], navIcon: "brands", showInNav: true,
} as const satisfies ProtectedRoute

export const BRANDS_MODULE = {
  name: "brands", protectedRoutes: [BRANDS_ROUTE],
} as const satisfies ModuleManifest
