"use client"
import { useState, useTransition } from "react"
import Link from "next/link"
import { RefreshCw, SlidersHorizontal, TriangleAlert } from "lucide-react"
import { useRouter } from "next/navigation"
import type { ApiListMeta } from "@/shared/api/response"
import { Button, Container, ErrorState, ListTableCard, PageHeader, Pagination,
  ICON_SIZE, StatusBadge, TableRow } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import type { DraftSummary, SourceInfo } from "../types"
import { draftMessages } from "../i18n"
import DraftFilters from "./DraftFilters"
import styles from "./drafts.module.css"
import { draftQueueHref, draftStage } from "../capabilities"
import DraftQueueNotice from "./DraftQueueNotice"

type ListResult<T> = { items: T[]; meta: ApiListMeta; errorMessage: string }
export default function DraftsView({ drafts, sources, source, seq, limit, sourceError,
  created, completed }: {
  drafts: ListResult<DraftSummary>; sources: SourceInfo[]; source: string;
  seq: number; limit: number; sourceError: string
  created?: string; completed?: boolean
}) {
  const t = useT(draftMessages)
  const router = useRouter()
  const [filterOpen, setFilterOpen] = useState(false)
  const [refreshing, startRefresh] = useTransition()
  const reload = () => startRefresh(() => router.refresh())
  const error = sourceError || drafts.errorMessage
  return <Container size="lg" padded>
    <PageHeader title={t("title")} subtitle={t("subtitle")}
      actions={[
        { label: t("refresh"), icon: <RefreshCw size={ICON_SIZE.md} />, refresh: true,
          onClick: reload, disabled: refreshing },
        { label: t(source ? "filtered" : "filter"), icon: <SlidersHorizontal size={ICON_SIZE.md} />,
          primary: true, onClick: () => setFilterOpen(true) },
        { label: t("reviewIssues"), icon: <TriangleAlert size={ICON_SIZE.md} />,
          onClick: () => router.push(`/product-drafts/issues${source
            ? `?source_key=${encodeURIComponent(source)}` : ""}`) },
      ]} />
    <DraftFilters key={filterOpen ? source : "closed"} sources={sources} source={source}
      open={filterOpen} onClose={() => setFilterOpen(false)} />
    <div className={styles.stack}>
      <DraftQueueNotice created={created} completed={completed} />
      {error && <ErrorState>{error}<Button variant="outlined"
        onClick={() => router.refresh()}>{t("retry")}</Button></ErrorState>}
      <ListTableCard headers={[t("received"), t("status"), t("sourceColumn"), t("actions")]}
        isEmpty={!drafts.items.length} emptyText={t("empty")}>
        {drafts.items.map((draft) => <TableRow key={draft.id}>
          <td data-label={t("received")}>
            {formatDateTime(draft.received_at, "Asia/Taipei")}</td>
          <td data-label={t("status")}>
            <StatusBadge label={t(draftStage(draft))} variant="muted" /></td>
          <td data-label={t("sourceColumn")} className={styles.wrap}>
            {sources.find((item) => item.source_key === draft.source_key)?.name
              ?? draft.source_key}</td>
          <td data-label={t("actions")}>
            {draftStage(draft) === "waiting" ? <Link href={draftQueueHref(draft.id, source)}>
              <Button as="span" variant="outlined">{t("open")}</Button></Link>
              : draftStage(draft) === "needsConfirmation" ? <Link
                href={`/product-drafts/issues?source_key=${encodeURIComponent(draft.source_key)}`}>
                {t("reviewIssues")}</Link>
                : <Button disabled variant="outlined">{t("open")}</Button>}
          </td>
        </TableRow>)}
      </ListTableCard>
      <Pagination meta={drafts.meta} seq={seq} limit={limit} />
    </div>
  </Container>
}
