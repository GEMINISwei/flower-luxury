import type { ModuleManifest, ProtectedRoute } from "@/shared/module"

export const LINE_GROUPS_ROUTE = {
  path: "/admin/line-groups", label: { zh: "群組設定", en: "LINE groups" },
  group: "admin", requires: ["*"], navIcon: "lineGroups", showInNav: true,
} as const satisfies ProtectedRoute
export const LINE_COLLECTION_MODULE = {
  name: "line_collection", protectedRoutes: [LINE_GROUPS_ROUTE],
} as const satisfies ModuleManifest
