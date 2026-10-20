"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, SelectInput, TextInput, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { ProductInfo, ProductStatus } from "../types"
import { productMessages } from "../i18n"
import { productCapabilities } from "../capabilities"
import { changeStatus, returnStatus } from "../actions"
import styles from "./catalog.module.css"

function StatusAction({ product, targets, returning }: {
  product: ProductInfo; targets: ProductStatus[]; returning: boolean
}) {
  const t = useT(productMessages)
  const router = useRouter()
  const [target, setTarget] = useState<ProductStatus>(targets[0])
  const [reason, setReason] = useState("")
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function save() {
    if (returning && !reason.trim()) { setError(t("required")); return }
    setError("")
    submit(() => returning ? returnStatus(product.id, target, reason)
      : changeStatus(product.id, target, reason),
    { onSuccess: () => router.refresh(), onError: setError })
  }
  return <form className={styles.stack} onSubmit={(event) => { event.preventDefault(); save() }}>
    <h3>{t(returning ? "return" : "forward")}</h3>
    {returning && <p className={styles.muted}>{t("returnHint")}</p>}
    <SelectInput label={t("target")} value={target} disabled={isPending}
      onChange={(value) => setTarget(value as ProductStatus)}
      options={targets.map((value) => ({ value, label: t(value) }))} />
    <TextInput label={t(returning ? "reasonRequired" : "reason")} value={reason}
      required={returning} onChange={setReason} disabled={isPending} />
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <div><Button type="submit" disabled={isPending} variant={returning ? "outlined" : "contained"}>
      {t(returning ? "return" : "forward")}</Button></div>
  </form>
}

export default function StatusPanel({ product }: { product: ProductInfo }) {
  const capabilities = productCapabilities(product.status)
  return <div className={styles.grid}>
    {capabilities.forward.length > 0 && <StatusAction product={product}
      targets={capabilities.forward} returning={false} />}
    {capabilities.returns.length > 0 && <StatusAction product={product}
      targets={capabilities.returns} returning />}
  </div>
}
