"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, ConfirmDialog, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { completeCollection } from "../actions"
import { collectionCapabilities } from "../capabilities"
import { draftMessages } from "../i18n"
import type { SourceInfo } from "../types"
import styles from "./drafts.module.css"

export default function CollectionPanel({ sources, scope }: {
  sources: SourceInfo[]; scope: string
}) {
  const t = useT(draftMessages)
  const router = useRouter()
  const [selected, setSelected] = useState<SourceInfo | null>(null)
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  const rounds = sources.filter((source) => (!scope || scope === source.source_key)
    && collectionCapabilities({ id: source.current_round_id,
      message_count: source.received_count ?? 0 }).canComplete)
  if (!rounds.length) return null
  return <section className={styles.panel} aria-label={t("collection")}>
    <h2>{t("collection")}</h2>
    {rounds.map((round) => <div className={styles.sectionHeader} key={round.source_key}>
      <div><p>{round.name}</p><p role="status">
        {t("receivedCount", { count: round.received_count ?? 0 })}</p></div>
      <Button disabled={isPending} onClick={() => { setSelected(round); setError("") }}>
        {t("completeCollection")}</Button>
    </div>)}
    <ConfirmDialog open={Boolean(selected)} title={t("completeCollection")}
      confirmText={t("completeCollection")} isPending={isPending} onClose={() => setSelected(null)}
      onConfirm={() => {
        const id = selected?.current_round_id
        if (id) submit(() => completeCollection(id), {
          onSuccess: () => { setSelected(null); router.refresh() }, onError: setError,
        })
      }}>
      <p>{t("completeHint")}</p>{error && <p role="alert">{error}</p>}
    </ConfirmDialog>
  </section>
}
