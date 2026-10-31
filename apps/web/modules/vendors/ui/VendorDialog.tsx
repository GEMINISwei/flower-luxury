"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { FormDialog, SelectInput, TextInput, useActionSubmit } from "@/shared/ui"
import { useLocale, useT } from "@/shared/i18n/context"
import { vendorMessages } from "../i18n"
import type { VendorInfo } from "../types"
import { validateVendor } from "../validation"
import { createVendor, updateVendor } from "../actions"

export default function VendorDialog({ vendor, onClose }: {
  vendor?: VendorInfo; onClose: () => void
}) {
  const t = useT(vendorMessages)
  const locale = useLocale()
  const router = useRouter()
  const initial = vendor ?? { name: "", note: "", is_active: true }
  const [name, setName] = useState(initial.name)
  const [note, setNote] = useState(initial.note ?? "")
  const [active, setActive] = useState(String(initial.is_active))
  const [errors, setErrors] = useState<{ name?: string }>({})
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function save() {
    const invalid = validateVendor({ name }, locale)
    setErrors(invalid); setError("")
    if (Object.keys(invalid).length) return
    const data = { name: name.trim(), note: note.trim() || null }
    submit(() => vendor ? updateVendor(vendor.id, { ...data, is_active: active === "true" })
      : createVendor(data), { onSuccess: () => { onClose(); router.refresh() }, onError: setError })
  }
  return <FormDialog title={t(vendor ? "entity" : "create")} open isPending={isPending}
    submitText={t("save")} onClose={onClose}
    onSubmit={(event) => { event.preventDefault(); save() }}>
    <TextInput label={t("name")} value={name} onChange={setName} required autoFocus
      disabled={isPending} error={errors.name} />
    <TextInput label={t("note")} value={note} onChange={setNote} disabled={isPending} />
    {vendor && <SelectInput label={t("status")} value={active} onChange={setActive}
      disabled={isPending} options={[
        { value: "true", label: t("active") }, { value: "false", label: t("inactive") },
      ]} />}
    {error && <p role="alert">{error}</p>}
  </FormDialog>
}
