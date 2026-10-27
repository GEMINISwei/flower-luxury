import type { Schema } from "@/shared/api/contract"

export type VendorInfo = Schema<"VendorInfo">
export type VendorCountry = VendorInfo["country"]
