"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { FormDialog, TextInput, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { productMessages } from "../i18n"
import { returnStatus } from "../actions"
import styles from "./catalog.module.css"

export default function ReturnStatusDialog({ id, onClose }: { id: string; onClose: () => void }) {
  const t = useT(productMessages)
  const router = useRouter()
  const [reason, setReason] = useState("")
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function save() {
    if (!reason.trim()) { setError(t("required")); return }
    setError("")
    submit(() => returnStatus(id, "not_acquired", reason), {
      onSuccess: () => { onClose(); router.refresh() }, onError: setError,
    })
  }
  return <FormDialog title={t("return")} open isPending={isPending}
    submitText={t("return")} onClose={onClose}
    onSubmit={(event) => { event.preventDefault(); save() }}>
    <p>{t("returnDescription")}</p>
    <TextInput label={t("reasonRequired")} value={reason} required disabled={isPending}
      onChange={(value) => { setReason(value); setError("") }} autoFocus />
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </FormDialog>
}
