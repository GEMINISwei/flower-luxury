import type { PhotoInfo, ProductStatus, StatusHistoryInfo } from "./types"

type Capabilities = { canEdit: boolean; canDelete: boolean; canReturn: boolean }
const CAPABILITIES: Record<ProductStatus, Capabilities> = {
  not_acquired: { canEdit: true, canDelete: true, canReturn: false },
  sold: { canEdit: false, canDelete: false, canReturn: true },
}

export function productCapabilities(status: ProductStatus): Capabilities {
  return CAPABILITIES[status]
}

export function gallerySelection(photos: readonly PhotoInfo[], selectedId: string | null) {
  const ordered = [...photos].sort((left, right) =>
    Number(right.is_main) - Number(left.is_main) || left.sort_order - right.sort_order)
  return {
    photos: ordered,
    selected: ordered.find((photo) => photo.id === selectedId) ?? ordered[0] ?? null,
  }
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
