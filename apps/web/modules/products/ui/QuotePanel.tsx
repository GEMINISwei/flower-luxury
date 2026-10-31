"use client"

import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, StatusBadge, Surface, useActionSubmit } from "@/shared/ui"
import { formatDateTime } from "@/shared/i18n/date-time"
import { useT } from "@/shared/i18n/context"
import type { VendorInfo } from "@/modules/vendors/public.client"
import type { ProductInfo, QuoteInfo, SaleInfo } from "../types"
import { quoteMessages } from "../i18n"
import { productCapabilities } from "../capabilities"
import { availableQuoteVendors, quoteCapabilities } from "../quote-capabilities"
import { deleteQuote } from "../actions"
import QuoteDialog from "./QuoteDialog"
import SaleDialog from "./SaleDialog"
import QuoteActionDialog from "./QuoteActionDialog"
import styles from "./catalog.module.css"

export default function QuotePanel({ product, quotes, vendors, currentSale, currentQuoteId }: {
  product: ProductInfo; quotes: QuoteInfo[]; vendors: VendorInfo[]
  currentSale: SaleInfo | null; currentQuoteId: string | null
}) {
  const t = useT(quoteMessages)
  const router = useRouter()
  const [editor, setEditor] = useState<QuoteInfo | "new" | null>(null)
  const [selected, setSelected] = useState<QuoteInfo | null>(null)
  const [error, setError] = useState("")
  const [action, setAction] = useState<QuoteInfo | null>(null)
  const { isPending, submit } = useActionSubmit()
  const { canEdit } = productCapabilities(product.status)
  const available = availableQuoteVendors(vendors, quotes)
  function act() {
    if (!action) return
    submit(() => deleteQuote(product.id, action.id), {
      onSuccess: () => { setAction(null); router.refresh() }, onError: setError,
    })
  }
  return <Surface className={styles.card}>
    {currentSale && <section aria-label={t("current")} className={styles.quote}>
      <h2>{t("current")}</h2>
      <dl className={styles.facts}>
        <div><dt>{t("vendor")}</dt><dd>{currentSale.vendor_name}</dd></div>
        <div><dt>{t("confirmAmount")}</dt><dd>{currentSale.amount_twd.toLocaleString()}</dd></div>
        <div><dt>{t("time")}</dt>
          <dd>{formatDateTime(currentSale.sold_at, "Asia/Taipei")}</dd></div>
      </dl>
    </section>}
    <div className={styles.cardHeader}><h2>{t("title")}</h2>
      {canEdit && <Button variant="outlined" disabled={!available.length}
        onClick={() => setEditor("new")}>
        {t("create")}</Button>}</div>
    <p className={styles.muted}>{t("rateHint")}</p>
    {!canEdit && <p className={styles.note}>{t("locked")}</p>}
    {!quotes.length && <p>{t("empty")}</p>}
    {canEdit && !vendors.length && <p>{t("vendorsHint")}</p>}
    {quotes.map((quote) => {
      const caps = quoteCapabilities(product.status, quote.has_sales)
      return <section key={quote.id} className={styles.quote} aria-label={quote.vendor_name}>
        <h3>{quote.vendor_name}</h3>
        {quote.id === currentQuoteId && <StatusBadge label={t("currentQuote")} variant="success" />}
        <dl className={styles.facts}>
          <div><dt>{t("amount")}</dt><dd>{quote.original_amount}</dd></div>
          <div><dt>{t("rate")}</dt><dd>{quote.exchange_rate}</dd></div>
          <div><dt>{t("twd")}</dt><dd>TWD {quote.amount_twd.toLocaleString()}</dd></div>
          {quote.note && <div><dt>{t("note")}</dt><dd>{quote.note}</dd></div>}
        </dl>
        {quote.has_sales && <p className={styles.muted}>{t("used")}</p>}
        <div className={styles.actions}>
          {caps.canEdit && <Button variant="outlined" disabled={isPending}
            onClick={() => setEditor(quote)}>{t("edit")}</Button>}
          {caps.canDelete && <Button variant="outlined" disabled={isPending}
            onClick={() => { setError(""); setAction(quote) }}>
            {t("delete")}</Button>}
          {caps.canConfirm && <Button disabled={isPending} onClick={() => setSelected(quote)}>
            {t("confirm")}</Button>}
        </div>
      </section>
    })}
    {canEdit && <Link href="/vendors" className={styles.link}>{t("manageVendors")}</Link>}
    {editor && <QuoteDialog key={editor === "new" ? "new" : editor.id}
      id={product.id}
      quote={editor === "new" ? undefined : editor} vendors={available}
      onClose={() => setEditor(null)} />}
    {selected && <SaleDialog product={product} quote={selected}
      onClose={() => setSelected(null)} />}
    <QuoteActionDialog action={action} isPending={isPending} error={error}
      onClose={() => setAction(null)} onConfirm={act} />
  </Surface>
}
