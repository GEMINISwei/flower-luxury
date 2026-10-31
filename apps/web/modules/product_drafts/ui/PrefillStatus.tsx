"use client"
import { useT } from "@/shared/i18n/context"
import { prefillMessages } from "../i18n"
import type { DraftInfo } from "../types"
import styles from "./drafts.module.css"

export default function PrefillStatus({ draft }: { draft: DraftInfo }) {
  const t = useT(prefillMessages)
  const status = !draft.prefill_configured ? "disabled"
    : draft.prefill_status === "disabled" ? "idle" : draft.prefill_status ?? "idle"
  return <div className={styles.panel}>
    <p className={styles.hint}>{t(status === "failed" ? "prefillFailed" : status)}</p>
  </div>
}
