"use client"

import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, Surface, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { VendorInfo } from "@/modules/vendors/public.client"
import type { ProductInfo, QuoteInfo } from "../types"
import { quoteMessages } from "../i18n"
import { productCapabilities } from "../capabilities"
import { availableQuoteVendors, quoteCapabilities } from "../quote-capabilities"
import { deleteQuote, refreshQuote } from "../actions"
import QuoteDialog from "./QuoteDialog"
import SaleDialog from "./SaleDialog"
import QuoteActionDialog from "./QuoteActionDialog"
import styles from "./catalog.module.css"

export default function QuotePanel({ product, quotes, vendors }: {
  product: ProductInfo; quotes: QuoteInfo[]; vendors: VendorInfo[]
}) {
  const t = useT(quoteMessages)
  const router = useRouter()
  const [editor, setEditor] = useState<QuoteInfo | "new" | null>(null)
  const [selected, setSelected] = useState<QuoteInfo | null>(null)
  const [error, setError] = useState("")
  const [action, setAction] = useState<{ quote: QuoteInfo; refreshing: boolean } | null>(null)
  const { isPending, submit } = useActionSubmit()
  const { canEdit } = productCapabilities(product.status)
  const available = availableQuoteVendors(vendors, quotes)
  function act() {
    if (!action) return
    const { quote, refreshing } = action
    submit(() => refreshing ? refreshQuote(product.id, quote.id)
      : deleteQuote(product.id, quote.id), {
      onSuccess: () => { setAction(null); router.refresh() }, onError: setError,
    })
  }
  return <Surface className={styles.card}>
    <div className={styles.actions}><h2>{t("title")}</h2>
      {canEdit && <Button variant="outlined" disabled={!available.length}
        onClick={() => setEditor("new")}>
        {t("create")}</Button>}</div>
    <p className={styles.muted}>{t("rateHint")}</p>
    {!canEdit && <p className={styles.note}>{t("locked")}</p>}
    {!quotes.length && <p>{t("empty")}</p>}
    {canEdit && !vendors.length && <p>{t("vendorsHint")}</p>}
    {quotes.map((quote) => {
      const caps = quoteCapabilities(product.status, quote.vendor_country, quote.has_sales)
      return <section key={quote.id} className={styles.quote}>
        <h3>{quote.vendor_name} · {t(quote.vendor_country)}</h3>
        <dl className={styles.facts}>
          <div><dt>{t("amount")}</dt><dd>{quote.currency} {quote.original_amount}</dd></div>
          <div><dt>{t("rate")}</dt><dd>{quote.exchange_rate}</dd></div>
          <div><dt>{t("twd")}</dt><dd>TWD {quote.amount_twd.toLocaleString()}</dd></div>
          {quote.note && <div><dt>{t("note")}</dt><dd>{quote.note}</dd></div>}
        </dl>
        {quote.has_sales && <p className={styles.muted}>{t("used")}</p>}
        <div className={styles.actions}>
          {caps.canEdit && <Button variant="outlined" disabled={isPending}
            onClick={() => setEditor(quote)}>{t("edit")}</Button>}
          {caps.canRefresh && <Button variant="outlined" disabled={isPending}
            onClick={() => { setError(""); setAction({ quote, refreshing: true }) }}>
            {t("refresh")}</Button>}
          {caps.canDelete && <Button variant="outlined" disabled={isPending}
            onClick={() => { setError(""); setAction({ quote, refreshing: false }) }}>
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
