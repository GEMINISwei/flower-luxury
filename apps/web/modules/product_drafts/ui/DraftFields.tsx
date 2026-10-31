"use client"
import { SelectInput, TextInput } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { BrandInfo } from "@/modules/brands/public.client"
import { CATEGORIES, productMessages } from "@/modules/products/public.client"
import type { DraftValues } from "../types"
import { draftMessages } from "../i18n"
import styles from "./drafts.module.css"

export default function DraftFields({ values, brands, disabled, onChange }: {
  values: DraftValues; brands: BrandInfo[]; disabled: boolean;
  onChange: (key: keyof DraftValues, value: string) => void
}) {
  const t = useT(draftMessages)
  const productT = useT(productMessages)
  const available = brands.filter((brand) => brand.is_active || brand.id === values.brand_id)
  return <section className={styles.panel} aria-label={t("fields")}>
    <h2>{t("fields")}</h2><p className={styles.hint}>{t("fieldsHint")}</p>
    <div className={styles.fields}>
      <TextInput label={t("name")} value={values.name} disabled={disabled}
        onChange={(value) => onChange("name", value)} />
      <TextInput label={t("cost_price")} value={values.cost_price} disabled={disabled} type="number"
        onChange={(value) => onChange("cost_price", value)} />
      <div className={styles.field}><span>{t("brand_id")}</span>
      <SelectInput ariaLabel={t("brand_id")} value={values.brand_id} disabled={disabled}
        onChange={(value) => onChange("brand_id", value)}
        options={[{ value: "", label: t("choose") },
          ...(values.brand_id && !brands.some((brand) => brand.id === values.brand_id)
            ? [{ value: values.brand_id, label: t("unavailableBrand") }] : []),
          ...available.map((brand) => ({
          value: brand.id, label: brand.is_active ? brand.name : `${brand.name} (${t("inactive")})`,
        }))]} /></div>
      <div className={styles.field}><span>{t("category")}</span>
      <SelectInput ariaLabel={t("category")} value={values.category} disabled={disabled}
        onChange={(value) => onChange("category", value)}
        options={[{ value: "", label: t("choose") }, ...Object.entries(CATEGORIES).map(([value, key]) => ({
          value, label: productT(key),
        }))]} /></div>
      {(["model_name", "serial_number", "year", "color"] as const).map((key) =>
        <TextInput key={key} label={t(key)} value={values[key]} disabled={disabled}
          type={key === "year" ? "number" : "text"}
          onChange={(value) => onChange(key, value)} />)}
      <label className={styles.notes}>{t("internal_note")}
        <textarea aria-label={t("internal_note")} value={values.internal_note} disabled={disabled}
          onChange={(event) => onChange("internal_note", event.target.value)} />
      </label>
    </div>
  </section>
}
