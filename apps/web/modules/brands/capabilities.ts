import type { BrandInfo } from "./types"

export function brandRemovalAction(brand: Pick<BrandInfo, "in_use" | "is_active">) {
  if (!brand.in_use) return "delete"
  return null
}
