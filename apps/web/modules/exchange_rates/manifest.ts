import type { ModuleManifest, ProtectedRoute } from "@/shared/module"

const EXCHANGE_ROUTE = {
  path: "/admin/exchange-rates", label: { zh: "匯率設定", en: "Exchange rate" },
  group: "admin", requires: ["*"], navIcon: "exchange", showInNav: true,
} as const satisfies ProtectedRoute

export const EXCHANGE_RATES_MODULE = {
  name: "exchange_rates", protectedRoutes: [EXCHANGE_ROUTE],
} as const satisfies ModuleManifest
