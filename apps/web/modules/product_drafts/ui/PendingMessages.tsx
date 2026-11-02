"use client"
import { useState } from "react"
import Image from "next/image"
import { Button, ConfirmDialog, Flex } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import type { ApiResponse } from "@/shared/api/contract"
import { resolvePendingMessage } from "../actions"
import { draftMessages } from "../i18n"
import type { DraftInfo } from "../types"
import styles from "./drafts.module.css"

type Mutation = (run: () => Promise<ApiResponse<DraftInfo>>) => void
export default function PendingMessages({ draft, disabled, mutate }: {
  draft: DraftInfo; disabled: boolean; mutate: Mutation
}) {
  const t = useT(draftMessages)
  const [ignoring, setIgnoring] = useState<string | null>(null)
  const messages = draft.pending_messages ?? []
  if (!messages.length) return null
  const resolve = (id: string, action: "accept" | "ignore") =>
    mutate(() => resolvePendingMessage(draft.id, draft.version, id, action))
  return <section className={styles.pendingPanel} role="region" aria-label={t("pendingTitle")}>
    <h2>{t("pendingTitle")} <span className={styles.count}>{messages.length}</span></h2>
    <p>{t("pendingHint")}</p>
    {messages.map((message) => <article key={message.id} className={styles.message}>
      <time className={styles.meta} dateTime={message.occurred_at}>
        {formatDateTime(message.occurred_at, "Asia/Taipei")}</time>
      {message.kind === "text" ? <p className={styles.pendingText}>{message.text}</p>
        : <div className={styles.imageMessage}>
          {message.photo?.url ? <Image src={`${message.photo.url}?size=320`} width={320}
            height={320} unoptimized alt={t("preview")} className={styles.messageThumbnail} />
            : <p>{t(message.photo?.status === "failed" ? "failedPhoto" : "pending")}</p>}
        </div>}
      <Flex gap={2}>
        <Button disabled={disabled} onClick={() => resolve(message.id, "accept")}>
          {t("accept")}</Button>
        <Button variant="outlined" disabled={disabled} onClick={() => setIgnoring(message.id)}>
          {t("ignore")}</Button>
      </Flex>
    </article>)}
    <ConfirmDialog title={t("ignore")} open={Boolean(ignoring)} isPending={disabled}
      confirmText={t("ignore")} onClose={() => setIgnoring(null)} onConfirm={() => {
        if (ignoring) resolve(ignoring, "ignore")
        setIgnoring(null)
      }}>
      <p>{t("ignoreHint")}</p>
    </ConfirmDialog>
  </section>
}
