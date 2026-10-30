"use client"
import { useState } from "react"
import Image from "next/image"
import { Button, Flex } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import { copyText, messageText } from "../capabilities"
import { draftMessages } from "../i18n"
import type { MessageInfo } from "../types"
import styles from "./drafts.module.css"

export default function MessageList({ messages, disabled, onMove, onCopy }: {
  messages: MessageInfo[]; disabled: boolean; onMove: (message: MessageInfo) => void;
  onCopy?: (success: boolean) => void
}) {
  const t = useT(draftMessages)
  const [copied, setCopied] = useState("")
  const [error, setError] = useState("")
  async function copy(text: string) {
    setCopied(""); setError("")
    const success = await copyText(text)
    if (onCopy) { onCopy(success); return }
    if (success) setCopied(t("copied"))
    else setError(t("copyFailed"))
  }
  return <section className={styles.stack} aria-label={t("messages")}>
    <div className={styles.sectionHeader}>
      <h2>{t("messages")} <span className={styles.count} aria-hidden="true">{messages.length}</span></h2>
      <Button variant="outlined" disabled={!messageText(messages)}
      onClick={() => void copy(messageText(messages))}>{t("copyAll")}</Button></div>
    <p className={styles.hint}>{t("copyHint")}</p>
    {copied && <p role="status">{copied}</p>}{error && <p role="alert">{error}</p>}
    <div className={styles.messageScroll} role="region" aria-label={t("messageContent")}
      tabIndex={0}>
      {messages.map((message) => <article key={message.id} className={styles.message}>
        <Flex gap={2} className={styles.meta}>
          <span>{message.sender_name ?? message.sender_id ?? t("unknownSender")}</span>
          <time dateTime={message.occurred_at}>{formatDateTime(message.occurred_at, "Asia/Taipei")}</time>
        </Flex>
        {message.kind === "text"
          ? <button type="button" className={styles.copyBlock}
            onClick={() => void copy(message.text ?? "")}>{message.text}</button>
          : <div className={styles.imageMessage}><p>{t("image")}</p>
            {message.photo?.url && <Image src={message.photo.url} width={240} height={240}
              unoptimized alt={t("preview")} className={styles.messageThumbnail} />}
            {message.photo && <p>{t(message.photo.status === "failed" ? "failedPhoto"
              : message.photo.status)}</p>}
          </div>}
        <Button variant="outlined" disabled={disabled} onClick={() => onMove(message)}>
          {t("moveMessage")}</Button>
      </article>)}
    </div>
    <p className={styles.hint}>{t("scrollHint")}</p>
  </section>
}
