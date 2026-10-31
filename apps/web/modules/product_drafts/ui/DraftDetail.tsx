"use client"
import { useState } from "react"
import { Button, ConfirmDialog, FormPageShell } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { BrandInfo } from "@/modules/brands/public.client"
import type { VendorInfo } from "@/modules/vendors/public.client"
import { discardDraft } from "../actions"
import { draftTextMessages } from "../capabilities"
import { draftMessages } from "../i18n"
import type { DraftInfo, SourceInfo } from "../types"
import DraftFields from "./DraftFields"
import DraftPhotos from "./DraftPhotos"
import DraftQuotes from "./DraftQuotes"
import PrefillStatus from "./PrefillStatus"
import MessageList from "./MessageList"
import useDraftEditor from "./useDraftEditor"
import styles from "./drafts.module.css"

export default function DraftDetail({ initial, brands, sources, vendors }: {
  initial: DraftInfo; brands: BrandInfo[]; sources: SourceInfo[]; vendors: VendorInfo[]
}) {
  const t = useT(draftMessages)
  const editor = useDraftEditor(initial)
  const { draft, values, pending } = editor
  const [dialog, setDialog] = useState<"approve" | "discard" | null>(null)
  const source = sources.find((item) => item.source_key === draft.source_key)
  function confirm() {
    setDialog(null)
    if (dialog === "approve") editor.save(true)
    else editor.run(() => discardDraft(draft.id, draft.version))
  }
  const disabled = pending || editor.stale
  return <FormPageShell title={t("detail")} subtitle={source?.name ?? draft.source_key}
    backHref="/product-drafts" backLabel={t("back")}
    actions={<div className={styles.headerActions}>
      <Button variant="outlined" disabled={pending} onClick={editor.reload}>{t("reload")}</Button>
      <Button variant="outlined" disabled={disabled} onClick={() => editor.save()}>{t("save")}</Button>
      <Button disabled={disabled} onClick={() => {
        if (editor.validate(true)) setDialog("approve")
      }}>{t("approve")}</Button>
      <Button variant="outlined" disabled={disabled} className={styles.dangerAction}
        onClick={() => setDialog("discard")}>{t("discard")}</Button>
    </div>}>
    <div className={styles.stack}>
      <div className={styles.feedback}>
        <p className={styles.hint}>{t("reloadHint")}</p>
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
          <DraftPhotos draft={draft} disabled={disabled} mutate={editor.run} />
          <div className={styles.panel}><MessageList messages={draftTextMessages(draft.messages)}
            onCopy={(success) => {
              editor.setStatus(success ? t("copied") : "")
              editor.setError(success ? "" : t("copyFailed"))
            }} /></div>
        </div>
        <div className={styles.editorColumn}>
          <PrefillStatus draft={draft} disabled={disabled} mutate={editor.run} />
          <DraftFields values={values} brands={brands} disabled={pending} onChange={editor.set} />
          <DraftQuotes draft={draft} vendors={vendors} disabled={disabled} mutate={editor.run} />
        </div>
      </div>
    </div>
    <ConfirmDialog title={t(dialog === "approve" ? "approve" : "discard")} open={Boolean(dialog)}
      isPending={pending} confirmText={t(dialog === "approve" ? "approve" : "discard")}
      onClose={() => setDialog(null)} onConfirm={confirm}>
      <p>{t(dialog === "approve" ? "approveHint" : "discardHint")}</p>
    </ConfirmDialog>
  </FormPageShell>
}
