import type { VendorInfo } from "./types"

export function vendorRemovalAction(vendor: Pick<VendorInfo, "has_quotes" | "is_active">) {
  if (!vendor.has_quotes) return "delete"
  return null
}
