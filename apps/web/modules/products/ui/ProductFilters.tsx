"use client"

import { FilterDialog } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { BrandInfo } from "@/modules/brands/public.client"
import { CATEGORIES } from "../constants"
import { productMessages } from "../i18n"

export default function ProductFilters({ brands, filters, open, onClose }: {
  brands: BrandInfo[]; filters: Record<string, string>; open: boolean; onClose: () => void
}) {
  const t = useT(productMessages)
  return <FilterDialog title={t("search")} open={open} onClose={onClose}
    initialValues={filters} fields={[
      { name: "keyword", label: t("keyword"), type: "text" },
      { name: "brand_id", label: t("brand_id"), type: "select",
        options: [{ value: "", label: t("all") },
          ...brands.map((brand) => ({ value: brand.id, label: brand.name }))] },
      { name: "status", label: t("status"), type: "select",
        options: [{ value: "", label: t("all") },
          ...(["not_acquired", "in_stock", "sold"] as const).map((value) =>
            ({ value, label: t(value) }))] },
      { name: "category", label: t("category"), type: "select",
        options: [{ value: "", label: t("all") },
          ...Object.entries(CATEGORIES).map(([value, key]) => ({ value, label: t(key) }))] },
      { name: "color", label: t("color"), type: "text" },
      { name: "year", label: t("year"), type: "text" },
    ]} />
}
