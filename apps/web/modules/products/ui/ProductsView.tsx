"use client"

import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { ChevronRight, ImageOff, Plus, SlidersHorizontal, RefreshCw } from "lucide-react"
import { Button, Container, ErrorState, ICON_SIZE, PageHeader, Pagination,
  StatusBadge, usePaginationResetHref } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import type { ApiListMeta } from "@/shared/api/response"
import type { BrandInfo } from "@/modules/brands/public.client"
import type { ProductInfo } from "../types"
import { productMessages } from "../i18n"
import ProductFilters from "./ProductFilters"
import styles from "./product-list.module.css"

export default function ProductsView({ products, brands, filters, meta, seq, errorMessage }: {
  products: ProductInfo[]; brands: BrandInfo[]; filters: Record<string, string>;
  meta: ApiListMeta; seq: number; errorMessage: string
}) {
  const t = useT(productMessages)
  const router = useRouter()
  const resetHref = usePaginationResetHref()
  const [filterOpen, setFilterOpen] = useState(false)
  return <Container size="lg" padded>
    <PageHeader title={t("title")} subtitle={t("subtitle")}
      actions={<Button icon={<Plus size={ICON_SIZE.md} />}
        onClick={() => router.push("/products/new")}>{t("create")}</Button>} />
    <div className={styles.toolbar}>
      <Link className={styles.clear} href="/products">{t("clear")}</Link>
      <div className={styles.actions}>
        {meta.hasPrevious && <Button variant="outlined" icon={<RefreshCw size={ICON_SIZE.sm} />}
          onClick={() => router.push(resetHref)}>{t("reload")}</Button>}
        <Button variant="outlined" icon={<SlidersHorizontal size={ICON_SIZE.sm} />}
          onClick={() => setFilterOpen(true)}>{t("filterTitle")}</Button>
      </div>
    </div>
    <ProductFilters key={filterOpen ? JSON.stringify(filters) : "closed"}
      brands={brands} filters={filters} open={filterOpen} onClose={() => setFilterOpen(false)} />
    {errorMessage && <ErrorState>{errorMessage}</ErrorState>}
    <div className={styles.tableCard}>
      <table className={styles.table}>
        <thead><tr>
          <th>{t("productColumn")}</th><th>{t("brand_id")}</th><th>{t("year")}</th>
          <th>{t("createdDate")}</th><th>{t("status")}</th>
          <th className={styles.amount}>{t("purchasePrice")}</th><th aria-label={t("detail")} />
        </tr></thead>
        <tbody>{products.map((product) => <tr key={product.id}>
          <td className={styles.primary}>
            <Link href={`/products/${product.id}`} className={styles.product}>
              <span className={styles.thumbnail}>
                {product.main_photo_id
                  ? <Image unoptimized width={64} height={64}
                    src={`/api/products/photos/${product.main_photo_id}/file`} alt="" />
                  : <ImageOff size={ICON_SIZE.md} aria-hidden />}
              </span>
              <span className={styles.identity}><strong>{product.name}</strong>
                <span className={styles.sku}>{product.sku}</span></span>
            </Link>
          </td>
          <td className={styles.meta} data-label={t("brand_id")}>{product.brand}</td>
          <td className={styles.meta} data-label={t("year")}>{product.year ?? "—"}</td>
          <td className={styles.date}>{formatDateTime(product.created_at, "Asia/Taipei").slice(0, 10)}</td>
          <td className={styles.status}><StatusBadge label={t(product.status)} variant="muted" /></td>
          <td className={styles.amount} data-label={t("purchasePrice")}>
            NT$ {product.cost_price.toLocaleString()}</td>
          <td className={styles.disclosure}><Link href={`/products/${product.id}`}
            aria-label={`${t("detail")} · ${product.name}`}>
            <ChevronRight size={ICON_SIZE.sm} aria-hidden /></Link></td>
        </tr>)}</tbody>
      </table>
      {!products.length && !errorMessage && <div className={styles.empty}>{t("empty")}</div>}
    </div>
    <Pagination meta={meta} seq={seq} limit={20} />
  </Container>
}
