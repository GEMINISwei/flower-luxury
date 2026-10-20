"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button, SelectInput, TextInput, useActionSubmit } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { BrandInfo } from "@/modules/brands/public.client"
import type { ProductCategory, ProductInfo } from "../types"
import { productMessages } from "../i18n"
import { CATEGORIES } from "../constants"
import { validateProduct } from "../validation"
import { createProduct, updateProduct } from "../actions"
import styles from "./catalog.module.css"

type Values = {
  name: string; brand_id: string; category: string; model_name: string; serial_number: string;
  color: string; year: string; cost_price: string; internal_note: string
}
function initial(product?: ProductInfo): Values {
  const blank: Values = { name: "", brand_id: "", category: "", model_name: "",
    serial_number: "", color: "", year: "", cost_price: "", internal_note: "" }
  return Object.fromEntries((Object.keys(blank) as (keyof Values)[]).map((field) =>
    [field, String(product?.[field] ?? "")])) as Values
}

export default function ProductForm({ product, brands }: {
  product?: ProductInfo; brands: BrandInfo[]
}) {
  const t = useT(productMessages)
  const locale = useLocale()
  const router = useRouter()
  const [values, setValues] = useState(() => initial(product))
  const [errors, setErrors] = useState<Partial<Record<keyof Values, string>>>({})
  const [failure, setFailure] = useState("")
  const [message, setMessage] = useState("")
  const { isPending, submit, fieldError } = useActionSubmit()
  function set(field: keyof Values, value: string) {
    setValues((previous) => ({ ...previous, [field]: value })); setMessage("")
    setErrors((previous) => ({ ...previous, [field]: undefined }))
  }
  function save() {
    const validation = validateProduct(values, locale)
    setErrors(validation); setFailure(""); setMessage("")
    if (Object.keys(validation).length) return
    const data = { ...values, category: values.category as ProductCategory,
      cost_price: Number(values.cost_price), year: values.year ? Number(values.year) : null }
    submit(async () => {
      const result = product ? await updateProduct(product.id, data) : await createProduct(data)
      if (result.status === "success") {
        router.push(`/products/${result.data.id}`)
      }
      return result
    }, { onSuccess: () => { setMessage(t("saved")); router.refresh() }, onError: setFailure })
  }
  const availableBrands = brands.filter((brand) =>
    brand.is_active || brand.id === product?.brand_id)
  return <form className={styles.stack} noValidate
    onSubmit={(event) => { event.preventDefault(); save() }}>
    <div className={styles.fields}>
      <TextInput label={t("name")} value={values.name}
        required disabled={isPending}
        onChange={(value) => set("name", value)} error={errors.name ?? fieldError("name")} />
      <SelectInput label={t("brand_id")} value={values.brand_id} required disabled={isPending}
        onChange={(value) => set("brand_id", value)}
        error={errors.brand_id ?? fieldError("brand_id")}
        options={[{ value: "", label: t("choose") },
          ...availableBrands.map((brand) => ({ value: brand.id, label: brand.name }))]} />
      <SelectInput label={t("category")} value={values.category} required disabled={isPending}
        onChange={(value) => set("category", value)}
        error={errors.category ?? fieldError("category")}
        options={[{ value: "", label: t("choose") },
          ...Object.entries(CATEGORIES).map(([value, key]) => ({ value, label: t(key) }))]} />
      {(["model_name", "serial_number", "color", "year", "cost_price"] as const).map((field) =>
        <TextInput key={field} label={t(field)} value={values[field]}
          type={field === "year" || field === "cost_price" ? "number" : "text"}
          required={field === "cost_price"} disabled={isPending}
          onChange={(value) => set(field, value)} error={errors[field] ?? fieldError(field)} />)}
    </div>
    <label className={styles.notes}>{t("internal_note")}
      <textarea value={values.internal_note} disabled={isPending}
        onChange={(event) => set("internal_note", event.target.value)} />
    </label>
    {!availableBrands.length && <p className={styles.note}>{t("brandsHint")}{" "}
      <Link className={styles.link} href="/brands">{t("manageBrands")}</Link></p>}
    {failure && <p role="alert" className={styles.error}>{failure}</p>}
    {message && <p role="status">{message}</p>}
    <div><Button type="submit" disabled={isPending || !availableBrands.length}>
      {isPending ? t("saving") : t("save")}</Button></div>
  </form>
}
