"use client"
import { FilterDialog } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { draftMessages } from "../i18n"
import type { SourceInfo } from "../types"

export default function DraftFilters({ sources, source, open, onClose }: {
  sources: SourceInfo[]; source: string; open: boolean; onClose: () => void
}) {
  const t = useT(draftMessages)
  return <FilterDialog title={t("filter")} open={open} onClose={onClose} resetText={t("clear")}
    initialValues={{ source_key: source }} fields={[
      { name: "source_key", label: t("source"), type: "select", options: [
        { value: "", label: t("all") },
        ...sources.map((item) => ({ value: item.source_key, label: item.name ?? item.source_key })),
      ] },
    ]} />
}
