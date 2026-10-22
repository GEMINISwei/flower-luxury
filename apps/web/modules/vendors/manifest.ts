import type { ModuleManifest, ProtectedRoute } from "@/shared/module"

const VENDORS_ROUTE = {
  path: "/vendors", label: { zh: "廠商", en: "Vendors" },
  group: "user", requires: [], navIcon: "vendors", showInNav: true,
} as const satisfies ProtectedRoute

export const VENDORS_MODULE = {
  name: "vendors", protectedRoutes: [VENDORS_ROUTE],
} as const satisfies ModuleManifest
