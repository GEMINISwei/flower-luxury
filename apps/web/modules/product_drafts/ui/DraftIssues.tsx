"use client"
import { useState, useTransition } from "react"
import { useRouter } from "next/navigation"
import { unstable_rethrow } from "next/navigation"
import { Button, ConfirmDialog, FormPageShell, Pagination, SelectInput } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import { getApiResponseErrorMessage } from "@/shared/api/error"
import type { ApiListMeta } from "@/shared/api/response"
import type { Schema } from "@/shared/api/contract"
import { resolveDraftIssue } from "../actions"
import { draftQueueHref } from "../capabilities"
import { issueMessages } from "../i18n"
import type { DraftSummary } from "../types"
import styles from "./drafts.module.css"

type Issue = Schema<"BufferedIssueInfo">
export default function DraftIssues({ issues, drafts, source, seq, error }: {
  issues: { items: Issue[]; meta: ApiListMeta; errorMessage: string };
  drafts: DraftSummary[]; source?: string; seq: number; error: string
}) {
  const t = useT(issueMessages)
  const router = useRouter()
  const [pending, startTransition] = useTransition()
  const [selected, setSelected] = useState<Record<string, string>>({})
  const [failure, setFailure] = useState("")
  const [removing, setRemoving] = useState<Issue | null>(null)
  const targets = drafts.filter((draft) => !draft.collecting && !draft.processing)
  function resolve(issue: Issue, action: "attach" | "discard") {
    const target = targets.find((draft) => draft.id === selected[issue.id]
      && draft.source_key === issue.source_key)
    if (action === "attach" && !target) return
    startTransition(async () => {
      setFailure("")
      try {
        const result = await resolveDraftIssue(issue.id, { action,
          ...(target ? { target_draft_id: target.id, target_version: target.version } : {}) })
        if (result.status === "success") { setRemoving(null); router.refresh() }
        else setFailure(getApiResponseErrorMessage(result, t("failed")))
      } catch (error) { unstable_rethrow(error); setFailure(t("failed")) }
    })
  }
  return <FormPageShell title={t("title")} backLabel={t("back")}
    backHref={draftQueueHref(undefined, source)} actions={[]}>
    <div className={styles.stack}>
      <p>{t("hint")}</p>
      {(failure || error || issues.errorMessage) && <p role="alert">
        {failure || error || issues.errorMessage}</p>}
      {!issues.items.length && <p role="status">{t("empty")}</p>}
      {issues.items.map((issue) => <article key={issue.id} className={styles.message}>
        <time dateTime={issue.occurred_at}>{formatDateTime(issue.occurred_at, "Asia/Taipei")}</time>
        <p className={styles.issueText}>{issue.kind === "image" ? t("image")
          : issue.kind === "start" || issue.kind === "end" ? `/${issue.kind}` : issue.text}</p>
        {issue.photo?.url ? <a href={issue.photo.url} target="_blank" rel="noreferrer">
          {t("viewPhoto")}</a> : issue.kind === "image" && <p>
          {t(issue.photo?.status === "failed" ? "failedPhoto" : "pending")}</p>}
        {(issue.kind === "text" || issue.kind === "image") && <>
          <SelectInput ariaLabel={t("target")} value={selected[issue.id] ?? ""} disabled={pending}
            onChange={(value) => setSelected((current) => ({ ...current, [issue.id]: value }))}
            options={[{ value: "", label: t("choose") }, ...targets
              .filter((draft) => draft.source_key === issue.source_key).map((draft) => ({
              value: draft.id, label: `${draft.fields.name ?? t("unnamed")} · ${
                formatDateTime(draft.received_at, "Asia/Taipei")}`,
            }))]} />
          <Button disabled={pending || !selected[issue.id]} onClick={() => resolve(issue, "attach")}>
            {t("attach")}</Button>
        </>}
        <Button variant="outlined" disabled={pending} onClick={() => setRemoving(issue)}>
          {t("discard")}</Button>
      </article>)}
      <Pagination meta={issues.meta} seq={seq} limit={20} />
    </div>
    <ConfirmDialog open={Boolean(removing)} title={t("discard")} confirmText={t("discard")}
      isPending={pending} onClose={() => setRemoving(null)}
      onConfirm={() => { if (removing) resolve(removing, "discard") }}>
      <p>{t("confirmDiscard")}</p>
    </ConfirmDialog>
  </FormPageShell>
}
