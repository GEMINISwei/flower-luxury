"use client"

import { ConfirmDialog } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { QuoteInfo } from "../types"
import { quoteMessages } from "../i18n"
import styles from "./catalog.module.css"

export default function QuoteActionDialog({ action, isPending, error, onClose, onConfirm }: {
  action: { quote: QuoteInfo; refreshing: boolean } | null
  isPending: boolean; error: string; onClose: () => void; onConfirm: () => void
}) {
  const t = useT(quoteMessages)
  const label = action?.refreshing ? "refresh" : "delete"
  return <ConfirmDialog title={t(label)} open={Boolean(action)} isPending={isPending}
    confirmText={t(label)} onClose={onClose} onConfirm={onConfirm}>
    <p>{action?.quote.vendor_name}</p>
    <p>{t(action?.refreshing ? "confirmRefresh" : "confirmDelete")}</p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </ConfirmDialog>
}
