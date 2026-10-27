"use client"

import { BadgeCheck, Search, type LucideIcon } from "lucide-react"
import { ICON_SIZE, Surface } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import type { ProductStatus, StatusHistoryInfo } from "../types"
import { statusTimeline } from "../capabilities"
import { productMessages } from "../i18n"
import styles from "./product-detail.module.css"

const STATUS_ICONS: Record<ProductStatus, LucideIcon> = { not_acquired: Search, sold: BadgeCheck }

export default function StatusTimeline({ histories, createdAt }: {
  histories: StatusHistoryInfo[]; createdAt: string
}) {
  const t = useT(productMessages)
  return <Surface className={styles.flowCard}>
    <h2>{t("flowHistory")}</h2>
    <ol className={styles.timeline}>{statusTimeline(histories, createdAt).map((event) => {
      const Icon = STATUS_ICONS[event.to_status]
      return <li key={event.id} className={styles.step}>
        <span className={styles.statusIcon}><Icon size={ICON_SIZE.lg} aria-hidden /></span>
        <strong>{t(event.to_status)}</strong>
        <time dateTime={event.changed_at}>{formatDateTime(event.changed_at, "Asia/Taipei").slice(0, 10)}</time>
        {event.operator_name && <span className={styles.eventNote}>{event.operator_name}</span>}
        {event.reason && <span className={styles.eventNote}>{event.reason}</span>}
      </li>
    })}</ol>
  </Surface>
}
