import type { ProductStatus, StatusHistoryInfo } from "./types"

export function productCapabilities(status: ProductStatus) {
  return { canEdit: status === "not_acquired", canDelete: status === "not_acquired" }
}

export function availableProductBrands<T extends { id: string; is_active: boolean }>(
  brands: readonly T[], existingId?: string,
): T[] {
  return brands.filter((brand) => brand.is_active || brand.id === existingId)
}

export function statusTimeline(histories: readonly StatusHistoryInfo[], createdAt: string) {
  const events = [...histories].sort((left, right) =>
    Date.parse(left.changed_at) - Date.parse(right.changed_at))
  if (!events.some((event) => event.action === "create")) {
    events.unshift({ id: "created", from_status: null, to_status: "not_acquired",
      action: "create", changed_at: createdAt, changed_by: "", operator_name: "", reason: null })
  }
  return events
}

export function productListQuery(filters: Record<string, string>) {
  const fields = ["keyword", "brand_id", "category", "status", "color", "year"]
  return Object.fromEntries(fields.filter((key) => filters[key]).map((key) => [key, filters[key]]))
}

export function canLoadMoreProducts(state: {
  mobile: boolean; intersecting: boolean; loading: boolean; errorMessage: string;
  hasNext: boolean; nextCursor: string | null
}) {
  return state.mobile && state.intersecting && !state.loading && !state.errorMessage
    && state.hasNext && Boolean(state.nextCursor)
}

export function appendProducts<T extends { id: string }>(current: T[], incoming: T[]): T[] {
  const seen = new Set(current.map((product) => product.id))
  return [...current, ...incoming.filter((product) => {
    if (seen.has(product.id)) return false
    seen.add(product.id)
    return true
  })]
}

