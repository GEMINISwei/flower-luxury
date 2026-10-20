"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button, Container, ErrorState, Flex, FormDialog, ListTableCard, PageHeader,
  SelectInput, StatusBadge, TableRow, TextInput, useActionSubmit } from "@/shared/ui"
import { useT } from "@/shared/i18n/context"
import { brandMessages } from "../i18n"
import type { BrandInfo } from "../types"
import { createBrand, deleteBrand, updateBrand } from "../actions"
import styles from "./brands.module.css"

export default function BrandsView({ brands, errorMessage }: {
  brands: BrandInfo[]; errorMessage: string
}) {
  const t = useT(brandMessages)
  const router = useRouter()
  const [selected, setSelected] = useState<BrandInfo | null>(null)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [active, setActive] = useState("true")
  const [error, setError] = useState("")
  const { isPending, submit } = useActionSubmit()
  function edit(brand: BrandInfo | null) {
    setSelected(brand); setName(brand?.name ?? ""); setActive(String(brand?.is_active ?? true))
    setError(""); setOpen(true)
  }
  function saved() { setOpen(false); setError(""); router.refresh() }
  function save() {
    if (!name.trim()) { setError(t("required")); return }
    submit(() => selected ? updateBrand(selected.id, name, active === "true") : createBrand(name),
      { onSuccess: saved, onError: setError })
  }
  function remove(brand: BrandInfo) {
    if (!window.confirm(t("confirm"))) return
    submit(() => deleteBrand(brand.id), { onSuccess: saved, onError: setError })
  }
  return <Container size="lg" padded>
    <PageHeader title={t("title")} subtitle={t("subtitle")}
      actions={<Button onClick={() => edit(null)}>{t("create")}</Button>} />
    {errorMessage && <ErrorState>{errorMessage}</ErrorState>}
    {!open && error && <p role="alert">{error}</p>}
    <ListTableCard headers={[t("name"), t("status"), t("actions")]}
      isEmpty={!brands.length} emptyText={t("empty")}>
      {brands.map((brand) => <TableRow key={brand.id}>
        <td data-label={t("name")}>{brand.name}</td>
        <td data-label={t("status")}><StatusBadge label={t(brand.is_active ? "active" : "inactive")}
          variant={brand.is_active ? "success" : "muted"} /></td>
        <td data-label={t("actions")}><Flex gap={2} className={styles.actions}>
          <Button variant="outlined" disabled={isPending} onClick={() => edit(brand)}>{t("edit")}</Button>
          <Button variant="outlined" disabled={isPending} onClick={() => remove(brand)}>{t("delete")}</Button>
        </Flex></td>
      </TableRow>)}
    </ListTableCard>
    <FormDialog title={t(selected ? "edit" : "create")} open={open} isPending={isPending}
      submitText={t("save")} onClose={() => setOpen(false)}
      onSubmit={(event) => { event.preventDefault(); save() }}>
      <TextInput label={t("name")} value={name} onChange={setName} required autoFocus />
      {selected && <SelectInput label={t("status")} value={active} onChange={setActive}
        options={[{ value: "true", label: t("active") }, { value: "false", label: t("inactive") }]} />}
      {error && <p role="alert">{error}</p>}
    </FormDialog>
  </Container>
}
