"use client"
import { useState } from "react"
import { RefreshCw } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import type { ApiListMeta } from "@/shared/api/response"
import { useT } from "@/shared/i18n/context"
import { Button, ConfirmDialog, Container, ErrorState, ListTableCard, PageHeader,
  ICON_SIZE, Pagination, StatusBadge, TableRow, useActionSubmit } from "@/shared/ui"
import { groupMessages } from "../i18n"
import { groupCapabilities } from "../capabilities"
import { stopGroup, updateGroup } from "../actions"
import type { GroupInfo } from "../types"
import styles from "./groups.module.css"
import GroupBatchState from "./GroupBatchState"

export default function GroupsView({ items, meta, errorMessage, seq, limit }: {
  items: GroupInfo[]; meta: ApiListMeta; errorMessage: string; seq: number; limit: number
}) {
  const t = useT(groupMessages)
  const router = useRouter()
  const [selected, setSelected] = useState<GroupInfo | null>(null)
  const [stopping, setStopping] = useState(false)
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function toggle() {
    if (!selected) return
    const action = stopping ? () => stopGroup(selected.id)
      : () => updateGroup(selected.id, !selected.enabled)
    submit(action, {
      onSuccess: () => { setSelected(null); setError(""); router.refresh() }, onError: setError,
    })
  }
  return <Container size="lg" padded>
    <PageHeader title={t("title")} subtitle={t("subtitle")}
      actions={[{ label: t("refresh"), icon: <RefreshCw size={ICON_SIZE.md} />,
        refresh: true, onClick: () => router.refresh() }]} />
    {errorMessage && <ErrorState>{errorMessage}</ErrorState>}
    <ListTableCard headers={[t("name"), t("bot"), t("status"), t("actions")]}
      isEmpty={!items.length} emptyText={t("empty")}>
      {items.map((group) => <TableRow key={group.id}>
        <td data-label={t("name")} className={styles.name}>{group.name ?? group.group_id}</td>
        <td data-label={t("bot")}><StatusBadge label={t(groupCapabilities(group).bot.label)}
          variant={groupCapabilities(group).bot.variant} /></td>
        <td data-label={t("status")}><GroupBatchState group={group} /></td>
        <td data-label={t("actions")}>
          <Button variant="outlined" disabled={isPending || !groupCapabilities(group).canToggle}
            onClick={() => { setSelected(group); setStopping(false); setError("") }}>
            {t(group.enabled ? "disable" : "enable")}</Button>
          {group.collecting && <Button variant="outlined" disabled={isPending}
            onClick={() => { setSelected(group); setStopping(true); setError("") }}>{t("stop")}</Button>}
          {group.review_product_id && <div className={styles.notice}>
            <p>{t("reviewHint")}</p><Link href={`/products/${group.review_product_id}`}>
              {t("review")}</Link></div>}
        </td>
      </TableRow>)}
    </ListTableCard>
    <Pagination meta={meta} seq={seq} limit={limit} />
    <ConfirmDialog title={t(stopping ? "stop" : selected?.enabled ? "disable" : "enable")} open={Boolean(selected)}
      isPending={isPending} confirmText={t(stopping ? "stop" : selected?.enabled ? "disable" : "enable")}
      onClose={() => setSelected(null)} onConfirm={toggle}>
      <p>{selected?.name ?? selected?.group_id}</p>
      <p>{t(stopping ? "stopHint" : selected?.enabled ? "disableHint" : "enableHint")}</p>
      {error && <p role="alert">{error}</p>}
    </ConfirmDialog>
  </Container>
}
