"use client"

import { StatusBadge, Surface } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { formatDateTime } from "@/shared/i18n/date-time"
import { quoteMessages } from "../i18n"
import type { SaleInfo } from "../types"
import styles from "./catalog.module.css"

export default function SaleHistory({ sales }: { sales: SaleInfo[] }) {
  const t = useT(quoteMessages)
  return <Surface className={styles.card}>
    <h2>{t("history")}</h2>
    {!sales.length && <p>{t("noSales")}</p>}
    {sales.map((sale) => <section className={styles.quote} key={sale.id}>
      <div className={styles.actions}><h3>{sale.vendor_name} · {t(sale.vendor_country)}</h3>
        <StatusBadge label={t(sale.is_current ? "current" : "returned")}
          variant={sale.is_current ? "success" : "muted"} /></div>
      <dl className={styles.facts}>
        <div><dt>{t("amount")}</dt><dd>{sale.currency} {sale.original_amount}</dd></div>
        <div><dt>{t("rate")}</dt><dd>{sale.exchange_rate}</dd></div>
        <div><dt>{t("confirmAmount")}</dt><dd>{sale.amount_twd.toLocaleString()}</dd></div>
        <div><dt>{t("cost")}</dt><dd>{sale.cost_price.toLocaleString()}</dd></div>
        <div><dt>{t("profit")}</dt><dd>{sale.profit_amount.toLocaleString()}</dd></div>
        <div><dt>{t("operator")}</dt><dd>{sale.operator_name}</dd></div>
        <div><dt>{t("time")}</dt><dd>{formatDateTime(sale.sold_at, "Asia/Taipei")}</dd></div>
        {sale.returned_at && <div><dt>{t("returnTime")}</dt>
          <dd>{formatDateTime(sale.returned_at, "Asia/Taipei")}</dd></div>}
        {sale.return_reason && <div><dt>{t("returnReason")}</dt><dd>{sale.return_reason}</dd></div>}
      </dl>
    </section>)}
  </Surface>
}
