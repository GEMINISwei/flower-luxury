"use client"

import { useRouter } from "next/navigation"
import { Filter, Plus, RefreshCw } from "lucide-react"
import { useT } from "@/shared/i18n/context"
import { ICON_SIZE } from "../internals"
import { usePaginationResetHref } from "../pagination"
import { uiMessages } from "../i18n"
import PageHeader from "./PageHeader"

type ListPageHeaderProps = {
  title: string
  subtitle: string
  showReset: boolean
  onFilter: () => void
  createAction?: { label: string; onClick: () => void }
}

export default function ListPageHeader({
  title, subtitle, showReset, onFilter, createAction,
}: ListPageHeaderProps) {
  const t = useT(uiMessages)
  const router = useRouter()
  const resetHref = usePaginationResetHref()
  return <PageHeader title={title} subtitle={subtitle} actions={[
    showReset && { label: t("refresh"), icon: <RefreshCw size={ICON_SIZE.md} />,
      refresh: true, onClick: () => router.push(resetHref) },
    { label: t("filter"), icon: <Filter size={ICON_SIZE.md} />, onClick: onFilter },
    createAction && { ...createAction, icon: <Plus size={ICON_SIZE.md} />, primary: true },
  ]} />
}
