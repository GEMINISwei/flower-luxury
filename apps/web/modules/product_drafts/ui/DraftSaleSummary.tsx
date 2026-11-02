"use client"
import { useLocale, useT } from "@/shared/i18n/context"
import type { VendorInfo } from "@/modules/vendors/public.client"
import { draftSaleSummary } from "../capabilities"
import { draftQuoteMessages } from "../i18n"
import type { DraftInfo } from "../types"

export default function DraftSaleSummary({ draft, vendors, cost }: {
  draft: DraftInfo; vendors: VendorInfo[]; cost: string
}) {
  const t = useT(draftQuoteMessages)
  const locale = useLocale()
  const summary = draftSaleSummary(draft.quotes ?? [], draft.selected_quote_id ?? null, cost)
  if (!summary) return null
  const vendor = vendors.find((item) => item.id === summary.quote.vendor_id)
  const number = (value: number) => new Intl.NumberFormat(locale).format(value)
  return <div>
    <p>{t("saleHint")}</p>
    <dl>
      <dt>{t("vendor")}</dt><dd>{vendor?.name ?? t("unavailable")}</dd>
      <dt>{t("amount")}</dt><dd>{summary.quote.original_amount}</dd>
      <dt>{t("rate")}</dt><dd>{summary.quote.exchange_rate}</dd>
      <dt>{t("saleAmount")}</dt><dd>{number(summary.amountTwd)}</dd>
      <dt>{t("cost")}</dt><dd>{number(summary.cost)}</dd>
      <dt>{t("profit")}</dt><dd>{number(summary.profit)}</dd>
    </dl>
    {summary.profit < 0 && <p role="alert">{t("loss", { amount: number(-summary.profit) })}</p>}
  </div>
}
