"use client"
import { useId, useState } from "react"
import { FormDialog, SelectInput, TextInput } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import type { ApiResponse } from "@/shared/api/contract"
import { getApiResponseErrorMessage } from "@/shared/api/error"
import type { VendorInfo } from "@/modules/vendors/public.client"
import { validateQuote } from "@/modules/products/public.client"
import { saveDraftQuote } from "../actions"
import { draftQuoteMessages } from "../i18n"
import type { DraftInfo, DraftQuoteInfo } from "../types"
import styles from "./drafts.module.css"

export default function DraftQuoteDialog({ draft, quote, vendors, disabled, mutate, onClose }: {
  draft: DraftInfo; quote?: DraftQuoteInfo; vendors: VendorInfo[]; disabled: boolean;
  mutate: (operation: () => Promise<ApiResponse<DraftInfo>>, onSuccess?: () => void) => void;
  onClose: () => void
}) {
  const t = useT(draftQuoteMessages)
  const locale = useLocale()
  const vendorInput = useId()
  const [vendorId, setVendorId] = useState(quote?.vendor_id ?? "")
  const [amount, setAmount] = useState(String(quote?.original_amount ?? ""))
  const [rate, setRate] = useState(String(quote?.exchange_rate ?? "1"))
  const [note, setNote] = useState(quote?.note ?? "")
  const [error, setError] = useState("")
  function save() {
    const vendor = vendors.find((item) => item.id === vendorId)
    if (!vendor) { setError(t("required")); return }
    const invalid = validateQuote(amount, rate, locale)
    if (invalid) { setError(invalid); return }
    setError("")
    mutate(async () => {
      const result = await saveDraftQuote(draft.id, draft.version, {
        vendor_id: vendorId, original_amount: amount, exchange_rate: rate,
        note: note.trim() || null }, quote?.id)
      if (result.status !== "success") setError(getApiResponseErrorMessage(result, t("failed")))
      return result
    }, onClose)
  }
  return <FormDialog open title={t(quote ? "edit" : "create")} isPending={disabled}
    submitText={t("save")} onClose={onClose}
    onSubmit={(event) => { event.preventDefault(); save() }}>
    <div className={styles.field}><label htmlFor={vendorInput}>{t("vendor")}*</label>
      <SelectInput id={vendorInput} ariaLabel={t("vendor")} value={vendorId}
        onChange={setVendorId} required disabled={disabled}
        options={[{ value: "", label: t("choose") }, ...vendors.filter((item) => item.is_active)
          .map((item) => ({ value: item.id, label: item.name }))]} /></div>
    <TextInput label={t("amount")} value={amount} onChange={setAmount} required disabled={disabled} />
    <TextInput label={t("rate")} value={rate} onChange={setRate} required disabled={disabled} />
    <TextInput label={t("note")} value={note} onChange={setNote} disabled={disabled} />
    {error && <p role="alert">{error}</p>}
  </FormDialog>
}
