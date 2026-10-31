"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, FormDialog, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import type { ProductInfo, QuoteInfo } from "../types"
import { quoteMessages } from "../i18n"
import { confirmSale } from "../actions"
import { salePreview } from "../quote-capabilities"
import styles from "./catalog.module.css"

export default function SaleDialog({ product, quote, onClose }: {
  product: ProductInfo; quote: QuoteInfo; onClose: () => void
}) {
  const t = useT(quoteMessages)
  const router = useRouter()
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  const { profit, loss, isLoss } = salePreview(quote.amount_twd, product.cost_price)
  const rows = [
    [t("vendor"), quote.vendor_name],
    [t("amount"), quote.original_amount],
    [t("rate"), quote.exchange_rate],
    [t("confirmAmount"), quote.amount_twd.toLocaleString()],
    [t("cost"), product.cost_price.toLocaleString()], [t("profit"), profit.toLocaleString()],
  ]
  function save() {
    submit(() => confirmSale(product.id, { quote_id: quote.id,
      quote_revision: quote.revision, cost_price: product.cost_price }),
    { onSuccess: () => { onClose(); router.refresh() }, onError: setError })
  }
  return <FormDialog title={t("confirm")} open isPending={isPending} submitText={t("confirm")}
    onClose={onClose} onSubmit={(event) => { event.preventDefault(); save() }}>
    <dl className={styles.facts}>{rows.map(([label, value]) => <div key={label}>
      <dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    {isLoss && <p className={styles.note}>
      {t("loss", { amount: loss.toLocaleString() })}</p>}
    <p>{t("confirmHint")}</p>
    {error && <><p role="alert" className={styles.error}>{error}</p>
      <Button variant="outlined" onClick={() => { onClose(); router.refresh() }}>
        {t("reload")}</Button></>}
  </FormDialog>
}
