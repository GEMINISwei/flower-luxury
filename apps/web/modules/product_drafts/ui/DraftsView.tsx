"use client"
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import type { ApiListMeta } from "@/shared/api/response"
import { Button, Container, ErrorState, ListTableCard, PageHeader, Pagination,
  StatusBadge, TableRow } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import type { DraftSummary, MessageInfo, SourceInfo } from "../types"
import { draftMessages } from "../i18n"
import DraftFilters from "./DraftFilters"
import LegacyMessages from "./LegacyMessages"
import styles from "./drafts.module.css"

type ListResult<T> = { items: T[]; meta: ApiListMeta; errorMessage: string }
export default function DraftsView({ drafts, messages, unassigned, sources, source,
  seq, limit, sourceError, hasLegacy }: {
  drafts: ListResult<DraftSummary> | null; messages: ListResult<MessageInfo> | null;
  unassigned: boolean; sources: SourceInfo[]; source: string; seq: number; limit: number;
  sourceError: string; hasLegacy: boolean
}) {
  const t = useT(draftMessages)
  const router = useRouter()
  const [filterOpen, setFilterOpen] = useState(false)
  const query = source ? `source_key=${encodeURIComponent(source)}` : ""
  const result = drafts ?? messages
  const error = sourceError || result?.errorMessage
  return <Container size="lg" padded>
    <PageHeader title={t(unassigned ? "legacy" : "title")} subtitle={t("subtitle")}
      actions={<>
        {!unassigned && <Button variant="outlined" onClick={() => setFilterOpen(true)}>
          {t(source ? "filtered" : "filter")}</Button>}
        <Button variant="outlined" onClick={() => router.refresh()}>{t("refresh")}</Button>
      </>} />
    <DraftFilters key={filterOpen ? source : "closed"} sources={sources} source={source}
      open={filterOpen} onClose={() => setFilterOpen(false)} />
    <div className={styles.stack}>
      {error && <ErrorState>{error}<Button variant="outlined"
        onClick={() => router.refresh()}>{t("retry")}</Button></ErrorState>}
      {drafts && <ListTableCard headers={[t("received"), t("status"), t("sourceColumn"), t("actions")]}
        isEmpty={!drafts.items.length} emptyText={t("empty")}>
        {drafts.items.map((draft) => <TableRow key={draft.id}>
          <td data-label={t("received")}>
            {formatDateTime(draft.received_at, "Asia/Taipei")}</td>
          <td data-label={t("status")}>
            <StatusBadge label={t(draft.collecting ? "collecting" : "waiting")} variant="muted" /></td>
          <td data-label={t("sourceColumn")} className={styles.wrap}>
            {sources.find((item) => item.source_key === draft.source_key)?.name
              ?? draft.source_key}</td>
          <td data-label={t("actions")}><Link href={`/product-drafts/${draft.id}`}>
            <Button as="span" variant="outlined">{t("open")}</Button></Link></td>
        </TableRow>)}
      </ListTableCard>}
      {messages && <LegacyMessages messages={messages.items} />}
      {result && <Pagination meta={result.meta} seq={seq} limit={limit} />}
      {hasLegacy && <Link href={`/product-drafts?view=messages&${query}`}>{t("legacy")}</Link>}
      {unassigned && <Link href={`/product-drafts?${query}`}>{t("back")}</Link>}
    </div>
  </Container>
}
