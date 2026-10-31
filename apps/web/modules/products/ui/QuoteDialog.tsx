"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { FormDialog, SelectInput, TextInput, useActionSubmit } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { VendorInfo } from "@/modules/vendors/public.client"
import type { QuoteInfo } from "../types"
import { quoteMessages } from "../i18n"
import { validateQuote } from "../quote-validation"
import { createQuote, updateQuote } from "../actions"

export default function QuoteDialog({ id, quote, vendors, onClose }: {
  id: string; quote?: QuoteInfo; vendors: VendorInfo[]; onClose: () => void
}) {
  const t = useT(quoteMessages)
  const locale = useLocale()
  const router = useRouter()
  const initial = quote ?? { vendor_id: "", original_amount: "", exchange_rate: "1", note: "" }
  const [vendorId, setVendorId] = useState(initial.vendor_id)
  const [amount, setAmount] = useState(initial.original_amount)
  const [rate, setRate] = useState(initial.exchange_rate
    .replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, ""))
  const [note, setNote] = useState(initial.note ?? "")
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function save() {
    if (!vendorId) { setError(t("required")); return }
    const invalid = validateQuote(amount, rate, locale)
    if (invalid) { setError(invalid); return }
    const data = { original_amount: amount, exchange_rate: rate, note: note.trim() || null }
    submit(() => quote ? updateQuote(id, quote.id, data)
      : createQuote(id, { ...data, vendor_id: vendorId }),
    { onSuccess: () => { onClose(); router.refresh() }, onError: setError })
  }
  return <FormDialog title={t(quote ? "entity" : "create")} open isPending={isPending}
    submitText={t("save")} onClose={onClose}
    onSubmit={(event) => { event.preventDefault(); save() }}>
    {quote ? <p>{t("vendor")}：{quote.vendor_name}</p>
      : <SelectInput label={t("vendor")} value={vendorId} onChange={setVendorId}
        required disabled={isPending} options={[{ value: "", label: t("choose") },
          ...vendors.map((vendor) => ({ value: vendor.id,
            label: vendor.name }))]} />}
    <TextInput label={t("amount")} value={amount} onChange={setAmount} required
      disabled={isPending} autoFocus />
    <TextInput label={t("rate")} value={rate} onChange={setRate} required disabled={isPending} />
    <TextInput label={t("note")} value={note} onChange={setNote} disabled={isPending} />
    {error && <p role="alert">{error}</p>}
  </FormDialog>
}
