"use client"

import { StatusBadge } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { ProductInfo } from "../types"
import { CATEGORIES } from "../constants"
import { productMessages } from "../i18n"
import styles from "./product-detail.module.css"

export default function ProductOverview({ product }: { product: ProductInfo }) {
  const t = useT(productMessages)
  return <div className={styles.hero}>
    <div className={styles.identity}>
      <div className={styles.meta}><StatusBadge label={t(product.status)}
        variant={product.status === "sold" ? "success" : "warning"} />
        <StatusBadge label={t(CATEGORIES[product.category])} variant="info" />
        <span>{product.sku}</span></div>
      <h2 className={styles.title}>{product.name}</h2>
      <p className={styles.brand}>{product.brand}</p>
    </div>
    <p className={styles.price} aria-label={t("cost_price")}>
      NT$ {product.cost_price.toLocaleString()}
    </p>
  </div>
}
