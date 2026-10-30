"use client"
import Link from "next/link"
import { useRouter } from "next/navigation"
import type { ApiListMeta } from "@/shared/api/response"
import { Button, Container, ErrorState, ListTableCard, PageHeader, Pagination,
  SelectInput, StatusBadge, TableRow } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import type { DraftSummary, MessageInfo, SourceInfo } from "../types"
import { draftMessages } from "../i18n"
import MessageList from "./MessageList"
import styles from "./drafts.module.css"

type ListResult<T> = { items: T[]; meta: ApiListMeta; errorMessage: string }
export default function DraftsView({ drafts, messages, unassigned, sources, source,
  seq, limit, sourceError }: {
  drafts: ListResult<DraftSummary> | null; messages: ListResult<MessageInfo> | null;
  unassigned: boolean; sources: SourceInfo[]; source: string; seq: number; limit: number;
  sourceError: string
}) {
  const t = useT(draftMessages)
  const router = useRouter()
  const query = source ? `source_key=${encodeURIComponent(source)}` : ""
  function filter(value: string) {
    const params = new URLSearchParams()
    if (value) params.set("source_key", value)
    if (unassigned) params.set("view", "messages")
    router.push(`/product-drafts?${params}`)
  }
  const result = drafts ?? messages
  const error = sourceError || result?.errorMessage
  return <Container size="lg" padded>
    <PageHeader title={t("title")} subtitle={t("subtitle")}
      actions={<Button variant="outlined" onClick={() => router.refresh()}>{t("refresh")}</Button>} />
    <div className={styles.stack}>
      <div className={styles.listToolbar}>
        <nav className={styles.tabs} aria-label={t("title")}>
          <Link aria-current={!unassigned ? "page" : undefined} href={`/product-drafts?${query}`}>
            {t("drafts")}</Link>
          <Link aria-current={unassigned ? "page" : undefined}
            href={`/product-drafts?view=messages&${query}`}>{t("unassigned")}</Link>
        </nav>
        <div className={styles.sourceFilter}><SelectInput label={t("source")} value={source} onChange={filter}
          options={[{ value: "", label: t("all") }, ...sources.map((item) => ({
            value: item.source_key, label: item.name ?? item.source_key,
          }))]} />
        </div>
      </div>
      {error && <ErrorState>{error}<Button variant="outlined"
        onClick={() => router.refresh()}>{t("retry")}</Button></ErrorState>}
      {drafts && <ListTableCard headers={[t("name"), t("source"), t("updated"), t("open")]}
        isEmpty={!drafts.items.length} emptyText={t("empty")}>
        {drafts.items.map((draft) => <TableRow key={draft.id}>
          <td data-label={t("name")}>{draft.fields.name || t("unnamed")}{" "}
            <StatusBadge label={t(draft.collecting ? "collecting" : "waiting")} variant="muted" /></td>
          <td data-label={t("source")} className={styles.wrap}>
            {sources.find((item) => item.source_key === draft.source_key)?.name
              ?? draft.source_key}</td>
          <td data-label={t("updated")}>
            {formatDateTime(draft.updated_at ?? draft.created_at, "Asia/Taipei")}</td>
          <td><Link href={`/product-drafts/${draft.id}`}>{t("open")}</Link></td>
        </TableRow>)}
      </ListTableCard>}
      {messages && <><p className={styles.hint}>{t("unassignedHint")}</p>
        {!messages.items.length && <p>{t("noMessages")}</p>}
        <MessageList messages={messages.items} /></>}
      {result && <Pagination meta={result.meta} seq={seq} limit={limit} />}
    </div>
  </Container>
}
