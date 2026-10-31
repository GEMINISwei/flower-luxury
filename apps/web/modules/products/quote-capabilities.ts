import type { ProductStatus } from "./types"

export function quoteCapabilities(status: ProductStatus, hasSales: boolean) {
  const canEdit = status !== "sold"
  return {
    canEdit, canDelete: canEdit && !hasSales,
    canConfirm: canEdit,
  }
}

export function availableQuoteVendors<T extends { id: string; is_active: boolean }>(
  vendors: readonly T[], quotes: readonly { vendor_id: string }[],
): T[] {
  const used = new Set(quotes.map((quote) => quote.vendor_id))
  return vendors.filter((vendor) => vendor.is_active && !used.has(vendor.id))
}

export function salePreview(amountTwd: number, cost: number) {
  const profit = amountTwd - cost
  return { profit, loss: Math.max(0, -profit), isLoss: profit < 0 }
}
