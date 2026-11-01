"use client"

import Link from "next/link"
import { useRef, useState } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { ChevronRight, ClipboardList, ImageOff, Plus, SlidersHorizontal, RefreshCw } from "lucide-react"
import { Button, Container, ErrorState, ICON_SIZE, PageHeader, Pagination,
  RouteLoading, StatusBadge, usePaginationResetHref } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import type { ApiListMeta } from "@/shared/api/response"
import type { BrandInfo } from "@/modules/brands/public.client"
import { DRAFTS_ROUTE } from "@/modules/product_drafts/public.client"
import type { ProductInfo } from "../types"
import { productMessages } from "../i18n"
import ProductFilters from "./ProductFilters"
import { useMobileProducts } from "./useMobileProducts"
import { useProductListState, useProductPosition } from "./useProductListState"
import styles from "./product-list.module.css"

export default function ProductsView({ products, brands, filters, meta, seq, errorMessage }: {
  products: ProductInfo[]; brands: BrandInfo[]; filters: Record<string, string>;
  meta: ApiListMeta; seq: number; errorMessage: string
}) {
  const t = useT(productMessages)
  const locale = useLocale()
  const router = useRouter()
  const resetHref = usePaginationResetHref()
  const [filterOpen, setFilterOpen] = useState(false)
  const sentinel = useRef<HTMLDivElement>(null)
  const state = useProductListState(filters)
  const mobile = useMobileProducts({ products, meta, filters, sentinel,
    errorFallback: t("failed"), restore: state.point, enabled: state.ready })
  useProductPosition(state.point, mobile.restoring)
  if (!state.ready) return <RouteLoading />
  return <Container size="lg" padded>
    <PageHeader title={t("title")} subtitle={t("subtitle")}
      actions={[
        { label: t("reload"), icon: <RefreshCw size={ICON_SIZE.md} />, refresh: true,
          onClick: () => { if (meta.hasPrevious) router.push(resetHref); else router.refresh() } },
        { label: t("filterTitle"), icon: <SlidersHorizontal size={ICON_SIZE.md} />,
          onClick: () => setFilterOpen(true) },
        { label: DRAFTS_ROUTE.label[locale], icon: <ClipboardList size={ICON_SIZE.md} />,
          onClick: () => router.push(DRAFTS_ROUTE.path) },
        { label: t("create"), icon: <Plus size={ICON_SIZE.md} />, primary: true,
          onClick: () => router.push("/products/new") },
      ]} />
    <ProductFilters key={filterOpen ? JSON.stringify(filters) : "closed"}
      brands={brands} filters={filters} open={filterOpen} onClose={() => setFilterOpen(false)}
      onApply={state.applyFilters} />
    {errorMessage && <ErrorState>{errorMessage}</ErrorState>}
    <div className={styles.tableCard}>
      <table className={styles.table}>
        <thead><tr>
          <th>{t("productColumn")}</th><th>{t("brand_id")}</th><th>{t("year")}</th>
          <th>{t("createdDate")}</th><th>{t("status")}</th>
          <th className={styles.amount}>{t("purchasePrice")}</th><th aria-label={t("detail")} />
        </tr></thead>
        <tbody>{mobile.products.map((product, index) => <tr key={product.id} id={`product-${product.id}`}
          className={index >= products.length ? styles.appended : undefined}>
          <td className={styles.primary}>
            <Link href={`/products/${product.id}`} className={styles.product}
              onClick={() => state.remember(product.id, mobile.products.length)}>
              <span className={styles.thumbnail}>
                {product.main_photo_id
                  ? <Image unoptimized width={64} height={64}
                    src={`/api/products/photos/${product.main_photo_id}/file?size=128`} alt="" />
                  : <ImageOff size={ICON_SIZE.md} aria-hidden />}
              </span>
              <span className={styles.identity}><strong>{product.name}</strong>
                <span className={styles.sku}>{product.sku}</span></span>
            </Link>
          </td>
          <td className={styles.brand} data-label={t("brand_id")}>{product.brand}</td>
          <td className={styles.year} data-label={t("year")}>{product.year ?? "—"}</td>
          <td className={styles.date} data-label={t("purchaseDate")}>
            {formatDateTime(product.created_at, "Asia/Taipei").slice(0, 10)}</td>
          <td className={styles.status}><StatusBadge label={t(product.status)} variant="muted" /></td>
          <td className={styles.amount} data-label={t("purchasePrice")}>
            NT$ {product.cost_price.toLocaleString()}</td>
          <td className={styles.disclosure}><Link href={`/products/${product.id}`}
            onClick={() => state.remember(product.id, mobile.products.length)}
            aria-label={`${t("detail")} · ${product.name}`}>
            <ChevronRight size={ICON_SIZE.sm} aria-hidden /></Link></td>
        </tr>)}</tbody>
      </table>
      {!products.length && !errorMessage && <div className={styles.empty}>{t("empty")}</div>}
    </div>
    <div className={styles.desktopPagination}><Pagination meta={meta} seq={seq} limit={20} /></div>
    <div className={styles.mobileLoading}>
      <div ref={sentinel} className={styles.sentinel} aria-hidden />
      <div role="status">{mobile.loading && t("loadingMore")}</div>
      {mobile.errorMessage && <>
        <ErrorState>{mobile.errorMessage}</ErrorState>
        <Button variant="outlined" onClick={mobile.retry}>{t("retry")}</Button>
      </>}
    </div>
  </Container>
}
