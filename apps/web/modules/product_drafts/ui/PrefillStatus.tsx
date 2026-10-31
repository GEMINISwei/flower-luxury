"use client"
import { Button } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { ApiResponse } from "@/shared/api/contract"
import { retryDraftPrefill } from "../actions"
import { prefillMessages } from "../i18n"
import type { DraftInfo } from "../types"
import styles from "./drafts.module.css"

export default function PrefillStatus({ draft, disabled, mutate }: {
  draft: DraftInfo; disabled: boolean;
  mutate: (operation: () => Promise<ApiResponse<DraftInfo>>) => void
}) {
  const t = useT(prefillMessages)
  const status = !draft.prefill_configured ? "disabled"
    : draft.prefill_status === "disabled" ? "idle" : draft.prefill_status ?? "idle"
  return <div className={styles.panel}>
    <p className={styles.hint}>{t(status === "failed" ? "prefillFailed" : status)}</p>
    <p className={styles.hint}>{t("protection")}</p>
    {status !== "disabled" && <div><Button variant="outlined" disabled={disabled}
      onClick={() => mutate(() => retryDraftPrefill(draft.id, draft.version))}>{t("retry")}</Button></div>}
  </div>
}
