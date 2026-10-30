"use client"
import { useState } from "react"
import Link from "next/link"
import { Button, ConfirmDialog, Container, Flex, PageHeader } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { BrandInfo } from "@/modules/brands/public.client"
import { discardDraft, reloadDraft } from "../actions"
import { draftMessages } from "../i18n"
import type { DraftInfo, MessageInfo, SourceInfo } from "../types"
import DraftFields from "./DraftFields"
import DraftPhotos from "./DraftPhotos"
import MessageList from "./MessageList"
import MoveMessageDialog from "./MoveMessageDialog"
import useDraftEditor from "./useDraftEditor"
import styles from "./drafts.module.css"

export default function DraftDetail({ initial, brands, sources }: {
  initial: DraftInfo; brands: BrandInfo[]; sources: SourceInfo[]
}) {
  const t = useT(draftMessages)
  const editor = useDraftEditor(initial)
  const { draft, values, pending } = editor
  const [dialog, setDialog] = useState<"approve" | "discard" | null>(null)
  const [moving, setMoving] = useState<MessageInfo | null>(null)
  const source = sources.find((item) => item.source_key === draft.source_key)
  function confirm() {
    setDialog(null)
    if (dialog === "approve") editor.save(true)
    else editor.run(() => discardDraft(draft.id, draft.version))
  }
  const disabled = pending || editor.stale
  return <Container size="lg" padded>
    <PageHeader title={t("detail")} subtitle={source?.name ?? draft.source_key}
      actions={<Link href="/product-drafts">{t("back")}</Link>} />
    <div className={styles.stack}>
      <div className={styles.feedback}>
        <div className={styles.reloadBar}>
          <p className={styles.hint}>{t("reloadHint")}</p>
          <Button variant="outlined" disabled={pending} onClick={editor.reload}>{t("reload")}</Button>
        </div>
        {editor.error && <p role="alert">{editor.error}</p>}
        {editor.status && <p role="status">{editor.status}</p>}
        {editor.dirty && <p className={styles.hint}>{t("unsaved")}</p>}
        {editor.comparison && <details open><summary>{t("latest")}</summary><dl>
          {Object.entries(editor.comparison.fields).map(([key, value]) => <div key={key}>
            <dt>{t(key as keyof typeof values)}</dt><dd>{String(value ?? "")}</dd>
          </div>)}
        </dl></details>}
      </div>
      <div className={styles.detailGrid}>
        <div className={styles.sourceColumn}>
          <DraftPhotos draft={draft} disabled={disabled}
            mutate={editor.run} onError={editor.setError} />
          <div className={styles.panel}><MessageList messages={draft.messages} disabled={disabled}
            onMove={setMoving}
            onCopy={(success) => {
              editor.setStatus(success ? t("copied") : "")
              editor.setError(success ? "" : t("copyFailed"))
            }} /></div>
        </div>
        <div className={styles.editorColumn}>
          <DraftFields values={values} brands={brands} disabled={pending} onChange={editor.set} />
          <Flex gap={3} className={styles.actions}>
            <Button variant="outlined" disabled={disabled} onClick={() => editor.save()}>{t("save")}</Button>
            <Button disabled={disabled} onClick={() => {
              if (editor.validate(true)) setDialog("approve")
            }}>{t("approve")}</Button>
            <Button variant="outlined" disabled={disabled} className={styles.dangerAction}
              onClick={() => setDialog("discard")}>{t("discard")}</Button>
          </Flex>
        </div>
      </div>
    </div>
    <ConfirmDialog title={t(dialog === "approve" ? "approve" : "discard")} open={Boolean(dialog)}
      isPending={pending} confirmText={t(dialog === "approve" ? "approve" : "discard")}
      onClose={() => setDialog(null)} onConfirm={confirm}>
      <p>{t(dialog === "approve" ? "approveHint" : "discardHint")}</p>
    </ConfirmDialog>
    {moving && <MoveMessageDialog message={moving} version={draft.version}
      onClose={() => setMoving(null)} onMoved={() => {
        setMoving(null); editor.run(() => reloadDraft(draft.id))
      }} />}
  </Container>
}
