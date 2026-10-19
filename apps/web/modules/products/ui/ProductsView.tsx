"use client"

import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { Container, ErrorState, ListPageHeader, Pagination, StatusBadge, Surface } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { ApiListMeta } from "@/shared/api/response"
import type { BrandInfo } from "@/modules/brands/public.client"
import type { ProductInfo } from "../types"
import { productMessages } from "../i18n"
import ProductFilters from "./ProductFilters"
import styles from "./catalog.module.css"

export default function ProductsView({ products, brands, filters, meta, seq, errorMessage }: {
  products: ProductInfo[]; brands: BrandInfo[]; filters: Record<string, string>;
  meta: ApiListMeta; seq: number; errorMessage: string
}) {
  const t = useT(productMessages)
  const router = useRouter()
  const [filterOpen, setFilterOpen] = useState(false)
  return <Container size="lg" padded>
    <ListPageHeader title={t("title")} subtitle={t("subtitle")} showReset={meta.hasPrevious}
      onFilter={() => setFilterOpen(true)}
      createAction={{ label: t("create"), onClick: () => router.push("/products/new") }} />
    <div className={styles.stack}>
      <ProductFilters key={filterOpen ? JSON.stringify(filters) : "closed"}
        brands={brands} filters={filters} open={filterOpen} onClose={() => setFilterOpen(false)} />
      <div><Link className={styles.link} href="/products">{t("clear")}</Link></div>
      {errorMessage && <ErrorState>{errorMessage}</ErrorState>}
      {!products.length && !errorMessage && <Surface className={styles.card}>{t("empty")}</Surface>}
      <div className={styles.grid}>{products.map((product) =>
        <Surface key={product.id} className={styles.card}>
          <Link href={`/products/${product.id}`} className={styles.link}>
            {product.main_photo_id && <Image unoptimized width={640} height={480}
              className={styles.cover} src={`/api/products/photos/${product.main_photo_id}/file`}
              alt={product.name} />}
            <h2>{product.name}</h2>
          </Link>
          <div className={styles.actions}><StatusBadge label={t(product.status)} variant="muted" />
            <span className={styles.muted}>{product.sku}</span></div>
          <p>{product.brand}</p><p>{t("cost_price")}: NT$ {product.cost_price.toLocaleString()}</p>
        </Surface>)}</div>
      <Pagination meta={meta} seq={seq} limit={20} />
    </div>
  </Container>
}
