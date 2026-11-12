"use client"
import { useT } from "@/shared/i18n/context"
import { Button } from "@/shared/ui"
import { canRetryPrefill } from "../capabilities"
import { prefillMessages } from "../i18n"
import type { DraftInfo } from "../types"
import styles from "./drafts.module.css"

export default function PrefillStatus({ draft, disabled, onRetry }: {
  draft: DraftInfo; disabled: boolean; onRetry: () => void
}) {
  const t = useT(prefillMessages)
  const status = !draft.prefill_configured ? "disabled"
    : draft.prefill_status === "disabled" ? "idle" : draft.prefill_status ?? "idle"
  return <div className={styles.panel}>
    <p className={styles.hint}>{t(status === "failed" ? "prefillFailed" : status)}</p>
    {canRetryPrefill(draft) && <Button type="button" onClick={onRetry} disabled={disabled}>
      {t("execute")}
    </Button>}
  </div>
}
