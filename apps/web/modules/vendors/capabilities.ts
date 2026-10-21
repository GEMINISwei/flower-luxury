import type { VendorInfo } from "./types"

export function vendorRemovalAction(vendor: Pick<VendorInfo, "country_locked" | "is_active">) {
  if (!vendor.country_locked) return "delete"
  return vendor.is_active ? "deactivate" : null
}
