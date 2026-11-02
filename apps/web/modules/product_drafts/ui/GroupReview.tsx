"use client"
import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { FileCheck2, RefreshCw, Trash2 } from "lucide-react"
import { Button, ConfirmDialog, FormPageShell, ICON_SIZE, SelectInput, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { discardDraft, finalizeDraft, moveDraftMessage, splitDraftMessage } from "../actions"
import { draftQueueHref, groupingCapabilities } from "../capabilities"
import { draftMessages } from "../i18n"
import type { DraftInfo, DraftSummary } from "../types"
import DraftPhotos from "./DraftPhotos"
import styles from "./drafts.module.css"

export default function GroupReview({ draft: initial, peers, scope }: {
  draft: DraftInfo; peers: DraftSummary[]; scope?: string
}) {
  const t = useT(draftMessages)
  const router = useRouter()
  const [draft, setDraft] = useState(initial)
  const [error, setError] = useState("")
  const [dialog, setDialog] = useState<"finalize" | "discard" | null>(null)
  const [target, setTarget] = useState("")
  const { isPending, submit } = useActionSubmit()
  const targets = peers.filter((peer) => peer.id !== draft.id && peer.requires_finalization
    && peer.source_key === draft.source_key && !peer.processing)
  const selected = targets.find((peer) => peer.id === target)
  const { canFinalize } = groupingCapabilities(draft)
  const refresh = () => router.refresh()
  return <FormPageShell title={t("groupReview")} subtitle={draft.source_key}
    backHref={draftQueueHref(undefined, scope)} backLabel={t("back")}
    actions={[{ label: t("refresh"), icon: <RefreshCw size={ICON_SIZE.md} />, refresh: true,
      disabled: isPending, onClick: refresh },
    { label: t("finalize"), icon: <FileCheck2 size={ICON_SIZE.md} />,
      primary: true, disabled: isPending || !canFinalize,
      onClick: () => setDialog("finalize") },
    { label: t("discard"), icon: <Trash2 size={ICON_SIZE.md} />, color: "error",
      disabled: isPending, onClick: () => setDialog("discard") }]}>
    <div className={styles.stack}>
      <p>{t("groupingHint")}</p>
      {!canFinalize && <p role="status">{t("originalRequired")}</p>}
      {draft.needs_confirmation && <Link
        href={`/product-drafts/issues?source_key=${encodeURIComponent(draft.source_key)}`}>
        {t("reviewIssues")}</Link>}
      {error && <p role="alert">{error}</p>}
      <DraftPhotos draft={draft} disabled={isPending} onError={setError}
        mutate={(run) => submit(async () => {
          const result = await run()
          if (result.status === "success") setDraft(result.data)
          return result
        }, { onSuccess: refresh, onError: setError })} />
      <section className={styles.panel} aria-label={t("messages")}>
        <h2>{t("messages")}</h2>
        <SelectInput ariaLabel={t("moveTarget")} value={target} onChange={setTarget}
          disabled={isPending} options={[{ value: "", label: t("choose") }, ...targets.map((peer) => ({
            value: peer.id, label: `${peer.fields.name ?? t("unnamed")} · ${peer.received_at}` }))]} />
        {draft.messages.map((message) => <article className={styles.message} key={message.id}>
          <time dateTime={message.occurred_at}>{message.occurred_at}</time>
          <p className={styles.issueText}>{message.kind === "text" ? message.text : t("image")}</p>
          <div className={styles.sectionHeader}>
            <Button variant="outlined" disabled={isPending || !selected} onClick={() => {
              if (selected) submit(() => moveDraftMessage(message.id, draft.version,
                selected.id, selected.version), { onSuccess: refresh, onError: setError })
            }}>{t("moveMessage")}</Button>
            <Button variant="outlined" disabled={isPending} onClick={() => submit(
              () => splitDraftMessage(message.id, draft.version), {
                onSuccess: refresh, onError: setError })}>{t("splitMessage")}</Button>
          </div>
        </article>)}
      </section>
    </div>
    <ConfirmDialog open={Boolean(dialog)} title={t(dialog ?? "finalize")}
      confirmText={t(dialog ?? "finalize")} isPending={isPending} onClose={() => setDialog(null)}
      onConfirm={() => submit(
        () => dialog === "discard" ? discardDraft(draft.id, draft.version)
          : finalizeDraft(draft.id, draft.version), {
          onSuccess: () => router.push(draftQueueHref(undefined, scope)), onError: setError })}>
      <p>{t(dialog === "discard" ? "discardHint" : "finalizeHint")}</p>
      {error && <p role="alert">{error}</p>}
    </ConfirmDialog>
  </FormPageShell>
}
