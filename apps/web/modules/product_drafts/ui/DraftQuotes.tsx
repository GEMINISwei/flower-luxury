"use client"
import { useState } from "react"
import { Button, ConfirmDialog } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { ApiResponse } from "@/shared/api/contract"
import type { VendorInfo } from "@/modules/vendors/public.client"
import { deleteDraftQuote } from "../actions"
import { draftQuoteMessages } from "../i18n"
import type { DraftInfo, DraftQuoteInfo } from "../types"
import DraftQuoteDialog from "./DraftQuoteDialog"
import styles from "./drafts.module.css"

export default function DraftQuotes({ draft, vendors, disabled, mutate }: {
  draft: DraftInfo; vendors: VendorInfo[]; disabled: boolean;
  mutate: (operation: () => Promise<ApiResponse<DraftInfo>>, onSuccess?: () => void) => void
}) {
  const t = useT(draftQuoteMessages)
  const locale = useLocale()
  const [editing, setEditing] = useState<DraftQuoteInfo | "new" | null>(null)
  const [removing, setRemoving] = useState<DraftQuoteInfo | null>(null)
  return <section aria-label={t("title")} className={styles.panel}>
    <div className={styles.sectionHeader}><h2>{t("title")}</h2>
      <Button variant="outlined" disabled={disabled} onClick={() => setEditing("new")}>{t("create")}</Button>
    </div>
    <p className={styles.hint}>{t("hint")}</p>
    {!draft.quotes?.length && <p className={styles.hint}>{t("empty")}</p>}
    {draft.quotes?.map((quote) => {
      const vendor = vendors.find((item) => item.id === quote.vendor_id)
      return <article key={quote.id} className={styles.message}>
        <div className={styles.sectionHeader}>
          <strong className={styles.wrap}>{vendor?.name ?? t("unavailable")}</strong>
          <span>{new Intl.NumberFormat(locale)
            .format(Number(quote.original_amount))} × {quote.exchange_rate}</span></div>
        {quote.note && <p className={styles.wrap}>{quote.note}</p>}
        <div className={styles.sectionHeader}>
          <Button variant="outlined" disabled={disabled} onClick={() => setEditing(quote)}>{t("edit")}</Button>
          <Button variant="outlined" disabled={disabled} onClick={() => setRemoving(quote)}>{t("delete")}</Button>
        </div>
      </article>
    })}
    {editing && <DraftQuoteDialog draft={draft} quote={editing === "new" ? undefined : editing}
      vendors={vendors} disabled={disabled} mutate={mutate} onClose={() => setEditing(null)} />}
    <ConfirmDialog open={Boolean(removing)} title={t("delete")} confirmText={t("delete")}
      isPending={disabled} onClose={() => setRemoving(null)} onConfirm={() => {
        if (removing) mutate(() => deleteDraftQuote(draft.id, draft.version, removing.id),
          () => setRemoving(null))
      }}><p>{t("confirm")}</p></ConfirmDialog>
  </section>
}
