"use client"

import { useState } from "react"
import Link from "next/link"
import { Pencil, Trash2, Undo2 } from "lucide-react"
import { FormPageShell, ICON_SIZE, Modal, Surface } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import type { BrandInfo } from "@/modules/brands/public.client"
import type { VendorInfo } from "@/modules/vendors/public.client"
import type { PhotoInfo, ProductInfo, QuoteInfo, SaleInfo } from "../types"
import { productMessages } from "../i18n"
import { productCapabilities, productSaleState } from "../capabilities"
import ProductForm from "./ProductForm"
import ProductOverview from "./ProductOverview"
import PhotoPanel from "./PhotoPanel"
import QuotePanel from "./QuotePanel"
import ReturnStatusDialog from "./ReturnStatusDialog"
import DeleteProductDialog from "./DeleteProductDialog"
import styles from "./product-detail.module.css"

export default function ProductDetail({
  product, brands, photos, vendors, quotes, sales,
}: {
  product: ProductInfo; brands: BrandInfo[]; photos: PhotoInfo[]
  vendors: VendorInfo[]; quotes: QuoteInfo[]; sales: SaleInfo[]
}) {
  const t = useT(productMessages)
  const [action, setAction] = useState<"edit" | "delete" | "return" | "photos" | null>(null)
  const caps = productCapabilities(product.status)
  const { currentSale, currentQuoteId } = productSaleState(product.status, sales)
  const basic = [
    [t("model_name"), product.model_name], [t("serial_number"), product.serial_number],
    [t("year"), product.year], [t("color"), product.color],
    [t("created"), formatDateTime(product.created_at, "Asia/Taipei").slice(0, 10)],
    [t("updated"), product.updated_at
      ? formatDateTime(product.updated_at, "Asia/Taipei").slice(0, 10) : null],
  ]
  return <FormPageShell title={t("detail")} subtitle={product.sku}
    backHref="/products" backLabel={t("back")} actions={[
      caps.canEdit && { label: t("edit"), icon: <Pencil size={ICON_SIZE.md} />,
        primary: true, onClick: () => setAction("edit") },
      caps.canDelete && { label: t("deleteProduct"), icon: <Trash2 size={ICON_SIZE.md} />,
        color: "error", onClick: () => setAction("delete") },
      caps.canReturn && { label: t("return"), icon: <Undo2 size={ICON_SIZE.md} />,
        primary: true, onClick: () => setAction("return") },
    ]}>
    <div className={styles.stack}>
      <section className={styles.summary}>
        <ProductOverview product={product} photos={photos} onPhotos={() => setAction("photos")} />
        <Surface className={styles.infoCard}>
          <h3>{t("basicInfo")}</h3>
          <dl className={styles.details}>
            {basic.map(([label, value]) => <div key={String(label)}>
              <dt>{label}</dt><dd>{String(value ?? "").trim() || "-"}</dd>
            </div>)}
            <div className={styles.notes}>
              <dt>{t("internal_note")}</dt><dd>{product.internal_note?.trim() || "-"}</dd>
            </div>
          </dl>
        </Surface>
      </section>
      <Link href={`/products/${product.id}/history`} className={styles.historyLink}>
        {t("viewHistory")}</Link>
      <QuotePanel product={product} quotes={quotes} vendors={vendors}
        currentSale={currentSale} currentQuoteId={currentQuoteId} />
    </div>
    {action === "photos" && <PhotoPanel id={product.id} name={product.name}
      photos={photos} status={product.status} onClose={() => setAction(null)} />}
    {action === "edit" && caps.canEdit && <Modal title={t("edit")} open
      onOpenChange={(open) => { if (!open) setAction(null) }}>
      <ProductForm key={product.id} product={product} brands={brands}
        onSaved={() => setAction(null)} />
    </Modal>}
    {action === "delete" && caps.canDelete && <DeleteProductDialog id={product.id}
      name={product.name} onClose={() => setAction(null)} />}
    {action === "return" && caps.canReturn && <ReturnStatusDialog id={product.id}
      onClose={() => setAction(null)} />}
  </FormPageShell>
}
