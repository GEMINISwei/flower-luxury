"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { ConfirmDialog, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { productMessages } from "../i18n"
import { deleteProduct } from "../actions"
import styles from "./catalog.module.css"

export default function DeleteProductDialog({ id, name, onClose }: {
  id: string; name: string; onClose: () => void
}) {
  const t = useT(productMessages)
  const router = useRouter()
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function remove() {
    submit(() => deleteProduct(id), {
      onSuccess: () => { router.push("/products"); router.refresh() }, onError: setError,
    })
  }
  return <ConfirmDialog title={t("deleteProduct")} open isPending={isPending}
    confirmText={t("deleteProduct")} onClose={onClose} onConfirm={remove}>
    <p>{name}</p><p>{t("deleteConfirm")}</p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </ConfirmDialog>
}
