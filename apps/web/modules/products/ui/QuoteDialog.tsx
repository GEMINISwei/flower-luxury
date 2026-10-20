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
  const initial = quote ?? { vendor_id: "", original_amount: "", note: "" }
  const [vendorId, setVendorId] = useState(initial.vendor_id)
  const [amount, setAmount] = useState(initial.original_amount)
  const [note, setNote] = useState(initial.note ?? "")
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  const selected = vendors.find((vendor) => vendor.id === vendorId)
  const country = quote?.vendor_country ?? selected?.country
  function save() {
    if (!country || !vendorId) { setError(t("required")); return }
    const invalid = validateQuote(amount, country, locale)
    if (invalid) { setError(invalid); return }
    const data = { original_amount: amount, note: note.trim() || null }
    submit(() => quote ? updateQuote(id, quote.id, data)
      : createQuote(id, { ...data, vendor_id: vendorId }),
    { onSuccess: () => { onClose(); router.refresh() }, onError: setError })
  }
  return <FormDialog title={t(quote ? "edit" : "create")} open isPending={isPending}
    submitText={t("save")} onClose={onClose}
    onSubmit={(event) => { event.preventDefault(); save() }}>
    {quote ? <p>{t("vendor")}：{quote.vendor_name} · {t(quote.vendor_country)}</p>
      : <SelectInput label={t("vendor")} value={vendorId} onChange={setVendorId}
        required disabled={isPending} options={[{ value: "", label: t("choose") },
          ...vendors.map((vendor) => ({ value: vendor.id,
            label: `${vendor.name} · ${t(vendor.country)} (${vendor.currency})` }))]} />}
    {country && <p>{t("currency")}：{quote?.currency ?? selected?.currency}</p>}
    <TextInput label={t("amount")} value={amount} onChange={setAmount} required
      disabled={isPending} autoFocus />
    <TextInput label={t("note")} value={note} onChange={setNote} disabled={isPending} />
    {quote && <p>{t("rate")}：{quote.exchange_rate}<br />{t("rateHint")}</p>}
    {error && <p role="alert">{error}</p>}
  </FormDialog>
}
