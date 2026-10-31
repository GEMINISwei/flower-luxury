import type { ModuleManifest, ProtectedRoute } from "@/shared/module"

export const DRAFTS_ROUTE = {
  path: "/product-drafts", label: { zh: "商品暫存", en: "Product drafts" },
  group: "user", requires: [], navIcon: "drafts", showInNav: true,
} as const satisfies ProtectedRoute
export const PRODUCT_DRAFTS_MODULE = {
  name: "product_drafts", protectedRoutes: [DRAFTS_ROUTE, {
    path: "/admin/draft-prefill", label: { zh: "審核預填設定", en: "Review prefill" },
    group: "admin", requires: ["*"], navIcon: "drafts", showInNav: true,
  }],
} as const satisfies ModuleManifest
