"use client"

import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, Container, StatusBadge, Surface, useActionSubmit } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { BrandInfo } from "@/modules/brands/public.client"
import type { PhotoInfo, ProductInfo, StatusHistoryInfo } from "../types"
import { productMessages } from "../i18n"
import { CATEGORIES, HISTORY_ACTION_LABELS } from "../constants"
import { productCapabilities } from "../capabilities"
import { deleteProduct } from "../actions"
import ProductForm from "./ProductForm"
import StatusPanel from "./StatusPanel"
import PhotoPanel from "./PhotoPanel"
import styles from "./catalog.module.css"

export default function ProductDetail({ product, brands, photos, histories }: {
  product: ProductInfo; brands: BrandInfo[]; photos: PhotoInfo[]; histories: StatusHistoryInfo[]
}) {
  const t = useT(productMessages)
  const locale = useLocale()
  const router = useRouter()
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  const { canEdit } = productCapabilities(product.status)
  function remove() {
    if (!window.confirm(t("deleteConfirm"))) return
    submit(() => deleteProduct(product.id), {
      onSuccess: () => { router.push("/products"); router.refresh() }, onError: setError,
    })
  }
  const basic = [
    [t("sku"), product.sku], [t("brand_id"), product.brand],
    [t("category"), t(CATEGORIES[product.category])],
    [t("cost_price"), `NT$ ${product.cost_price.toLocaleString()}`],
    [t("model_name"), product.model_name], [t("serial_number"), product.serial_number],
    [t("color"), product.color],
    [t("year"), product.year], [t("internal_note"), product.internal_note],
  ]
  return <Container size="lg" padded><div className={styles.stack}>
    <Link className={styles.link} href="/products">{t("back")}</Link>
    <Surface className={styles.card}>
      <div className={styles.actions}>
      <StatusBadge label={t(product.status)} variant="muted" /><span>{product.sku}</span></div>
      <h1>{product.name}</h1>
      {!canEdit && <p className={styles.note}>{t("locked")}</p>}
      <dl className={styles.details}>{basic.map(([label, value]) =>
        <div key={String(label)}><dt>{label}</dt><dd>{value || "—"}</dd></div>)}</dl>
      {canEdit && <div><Button variant="outlined" disabled={isPending} onClick={remove}>
        {t("deleteProduct")}</Button></div>}
      {error && <p role="alert" className={styles.error}>{error}</p>}
    </Surface>
    <Surface className={styles.card}>
      <StatusPanel key={product.status} product={product} /></Surface>
    <Surface className={styles.card}>
      <PhotoPanel id={product.id} photos={photos} canEdit={canEdit} /></Surface>
    {canEdit && <Surface className={styles.card}><h2>{t("edit")}</h2>
      <ProductForm key={product.id} product={product} brands={brands} />
    </Surface>}
    <Surface className={styles.card}><h2>{t("history")}</h2>
      <ol className={styles.history}>{histories.map((row) => <li key={row.id}>
        <strong>{row.from_status ? `${t(row.from_status)} → ` : ""}{t(row.to_status)}</strong>
        <span>{row.operator_name} · {new Date(row.changed_at).toLocaleString(
            locale === "zh" ? "zh-TW" : "en-US", { timeZone: "Asia/Taipei" },
          )}</span>
        <span className={styles.muted}>{row.changed_by}</span>
        <span>{row.reason || t(HISTORY_ACTION_LABELS[row.action] ?? "changed")}</span>
      </li>)}</ol>
    </Surface>
  </div></Container>
}
