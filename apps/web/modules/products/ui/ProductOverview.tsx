"use client"

import Image from "next/image"
import { ImagePlus, Images } from "lucide-react"
import { ICON_SIZE, StatusBadge } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { PhotoInfo, ProductInfo } from "../types"
import { gallerySelection, productCapabilities } from "../capabilities"
import { CATEGORIES } from "../constants"
import { productMessages } from "../i18n"
import styles from "./product-detail.module.css"

export default function ProductOverview({ product, photos, onPhotos }: {
  product: ProductInfo; photos: PhotoInfo[]; onPhotos: () => void
}) {
  const t = useT(productMessages)
  const gallery = gallerySelection(photos, null)
  const caps = productCapabilities(product.status)
  const emptyLabel = caps.canEdit ? t("addPhotos") : t("noPhotos")
  return <div className={styles.hero}>
    <button type="button" className={styles.mainPhotoTrigger} onClick={onPhotos}
      aria-label={gallery.selected ? t("openPhotos") : emptyLabel}>
      {gallery.selected ? <>
        <Image unoptimized width={160} height={160} src={gallery.selected.url} alt={product.name}
          className={styles.mainImage} />
        <span className={styles.photoCount}><Images size={ICON_SIZE.sm} aria-hidden />
          {t("photoCount", { count: photos.length })}</span>
      </> : <span className={styles.photoPlaceholder}>
        <ImagePlus size={ICON_SIZE.lg} aria-hidden /><span>{emptyLabel}</span>
      </span>}
    </button>
    <div className={styles.identity}>
      <div className={styles.meta}><StatusBadge label={t(product.status)}
        variant={caps.canReturn ? "success" : "warning"} />
        <StatusBadge label={t(CATEGORIES[product.category])} variant="info" />
        <span>{product.sku}</span></div>
      <h2 className={styles.title}>{product.name}</h2>
      <p className={styles.brand}>{product.brand}</p>
    </div>
    <p className={styles.price} aria-label={t("cost_price")}>
      <span className={styles.priceLabel}>{t("purchaseAmount")}</span>
      <span>NT$ {product.cost_price.toLocaleString()}</span>
    </p>
  </div>
}
