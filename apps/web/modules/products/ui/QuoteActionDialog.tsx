"use client"

import { ConfirmDialog } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { QuoteInfo } from "../types"
import { quoteMessages } from "../i18n"
import styles from "./catalog.module.css"

export default function QuoteActionDialog({ action, isPending, error, onClose, onConfirm }: {
  action: QuoteInfo | null
  isPending: boolean; error: string; onClose: () => void; onConfirm: () => void
}) {
  const t = useT(quoteMessages)
  return <ConfirmDialog title={t("delete")} open={Boolean(action)} isPending={isPending}
    confirmText={t("delete")} onClose={onClose} onConfirm={onConfirm}>
    <p>{action?.vendor_name}</p>
    <p>{t("confirmDelete")}</p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </ConfirmDialog>
}
