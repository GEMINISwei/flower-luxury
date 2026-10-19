import type { ProductStatus } from "./types"

type Capabilities = { canEdit: boolean; forward: ProductStatus[]; returns: ProductStatus[] }
const CAPABILITIES: Record<ProductStatus, Capabilities> = {
  not_acquired: { canEdit: true, forward: ["in_stock", "sold"], returns: [] },
  in_stock: { canEdit: true, forward: ["sold"], returns: ["not_acquired"] },
  sold: { canEdit: false, forward: [], returns: ["in_stock", "not_acquired"] },
}

export function productCapabilities(status: ProductStatus): Capabilities {
  return CAPABILITIES[status]
}
