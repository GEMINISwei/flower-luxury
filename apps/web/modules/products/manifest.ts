import type { ModuleManifest, ProtectedRoute } from "@/shared/module"

export const PRODUCTS_PATH = "/products"
const PRODUCTS_ROUTE = {
  path: PRODUCTS_PATH, label: { zh: "商品", en: "Products" },
  group: "user", requires: [], navIcon: "products", showInNav: true,
} as const satisfies ProtectedRoute

export const PRODUCTS_MODULE = {
  name: "products", protectedRoutes: [PRODUCTS_ROUTE],
} as const satisfies ModuleManifest
